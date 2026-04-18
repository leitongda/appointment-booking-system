"""
支付状态主动对账 Celery 任务。
- 每 15 分钟扫描 status=0（待支付）且创建在 5~60 分钟之间的预约
- 调用微信支付查询接口确认实际支付状态
- 如果微信侧已支付成功，更新本地状态为 CONFIRMED
- 支持多租户隔离
"""
import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.middleware.tenant_context import set_tenant_context, clear_tenant_context
from app.models.appointment import Appointment
from app.models.miniapp_platform import PaymentProfile
from app.models.tenant import Tenant
from app.modules.appointments.common import APPOINTMENT_STATUS

logger = logging.getLogger(__name__)

# 对账时间窗口（分钟）
RECONCILIATION_MIN_MINUTES = 5
RECONCILIATION_MAX_MINUTES = 60


@celery_app.task(
    name="payment.reconciliation",
    queue="scheduled",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def reconcile_pending_payments(self):
    """
    主动对账：查询微信支付状态，补齐遗漏的支付成功回调。
    扫描所有活跃租户的待支付预约，向微信确认实际支付状态。
    """
    logger.info("开始支付状态主动对账...")

    try:
        db_gen = get_sync_db()
        db = next(db_gen)
        try:
            # 查询所有活跃租户
            tenants = db.execute(
                select(Tenant.id).where(Tenant.status == 1)
            ).scalars().all()

            now = datetime.now()
            min_threshold = now - timedelta(minutes=RECONCILIATION_MAX_MINUTES)
            max_threshold = now - timedelta(minutes=RECONCILIATION_MIN_MINUTES)

            total_reconciled = 0

            for tenant_id in tenants:
                try:
                    set_tenant_context(tenant_id)
                    reconciled = _reconcile_tenant_payments(
                        db, tenant_id, min_threshold, max_threshold
                    )
                    total_reconciled += reconciled
                except Exception as e:
                    logger.error(f"租户 {tenant_id} 支付对账失败: {e}", exc_info=True)
                finally:
                    clear_tenant_context()

            logger.info(f"支付状态主动对账完成，共补齐 {total_reconciled} 条支付记录")

        finally:
            db_gen.close()

    except Exception as exc:
        logger.error(f"支付状态主动对账任务失败: {exc}", exc_info=True)
        raise self.retry(exc=exc)


def _reconcile_tenant_payments(
    db, tenant_id: str, min_threshold: datetime, max_threshold: datetime
) -> int:
    """对账单个租户的待支付预约。"""
    from app.infrastructure.payments.wechat_pay_service import WeChatPayService

    # 查找时间窗口内的待支付预约（需要有支付配置才能查询微信）
    pending_appointments = db.execute(
        select(Appointment)
        .options(
            selectinload(Appointment.payment_profile),
        )
        .where(
            Appointment.tenant_id == tenant_id,
            Appointment.status == 0,  # 待支付
            Appointment.created_at >= min_threshold,
            Appointment.created_at <= max_threshold,
            Appointment.payment_profile_id.isnot(None),  # 需要有支付配置
        )
    ).scalars().all()

    reconciled = 0

    for appointment in pending_appointments:
        try:
            payment_profile = appointment.payment_profile
            if not payment_profile:
                logger.debug(
                    f"预约 {appointment.appointment_no} 缺少支付配置，跳过"
                )
                continue

            # 生成商户订单号（与 PaymentService._generate_out_trade_no 规则一致）
            if not appointment.appointment_no:
                logger.warning(
                    f"预约 {appointment.id} 缺少 appointment_no，跳过对账"
                )
                continue
            out_trade_no = appointment.appointment_no

            # 调用微信支付查询接口
            # WeChatPayService.query_order 是 async def，必须在同步 worker 里 asyncio.run 包装。
            # 否则只会拿到一个未 await 的 coroutine（truthy 但没有 .get），导致对账永久空跑。
            wxpay_service = WeChatPayService(payment_profile=payment_profile)
            try:
                order_info = asyncio.run(wxpay_service.query_order(out_trade_no))
            except Exception as query_exc:
                logger.warning(
                    f"查询微信订单失败: out_trade_no={out_trade_no}, error={query_exc}"
                )
                continue

            if not order_info:
                logger.warning(
                    f"查询订单失败: out_trade_no={out_trade_no}"
                )
                continue

            trade_state = order_info.get("trade_state")

            # 如果微信侧已支付成功
            if trade_state == "SUCCESS":
                transaction_id = order_info.get("transaction_id")

                # 使用条件更新避免并发问题
                update_result = db.execute(
                    update(Appointment)
                    .where(
                        Appointment.id == appointment.id,
                        Appointment.status == 0,  # 仍然是待支付
                    )
                    .values(
                        status=APPOINTMENT_STATUS["CONFIRMED"],
                        payment_transaction_id=transaction_id,
                        paid_at=datetime.now(),
                    )
                )

                if update_result.rowcount:
                    logger.info(
                        f"支付对账成功补齐: appointment_no={appointment.appointment_no}, "
                        f"transaction_id={transaction_id}"
                    )
                    reconciled += 1
                else:
                    logger.info(
                        f"预约在查询期间状态已变更，跳过: "
                        f"appointment_no={appointment.appointment_no}"
                    )
            elif trade_state in ("NOTPAY", "USERPAYING", "PAY_ERROR", "REFUND", "CLOSED", "REVOKED"):
                # 其他终态，记录日志但不做处理
                logger.debug(
                    f"订单状态: {trade_state}, out_trade_no={out_trade_no}"
                )

        except Exception as e:
            logger.error(
                f"对账预约 {appointment.appointment_no} 失败: {e}",
                exc_info=True,
            )

    if reconciled > 0:
        db.commit()

    return reconciled
