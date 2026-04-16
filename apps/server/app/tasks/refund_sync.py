"""
退款状态主动同步 Celery 任务。
- 每 30 分钟扫描 status='processing' 且 updated_at < 30 分钟前的退款记录
- 调用微信退款查询接口确认实际退款状态
- 根据微信侧结果更新本地 RefundRecord 状态
- 调用 RefundService.sync_appointment_refund_state() 聚合到 Appointment
- 支持多租户隔离
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.middleware.tenant_context import set_tenant_context, clear_tenant_context
from app.models.miniapp_platform import PaymentProfile
from app.models.refund import RefundRecord
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

# 同步时间阈值（分钟）- 超过此时长的 processing 状态记录需要主动查询
REFUND_SYNC_THRESHOLD_MINUTES = 30


@celery_app.task(
    name="refund.status_sync",
    queue="scheduled",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def sync_refund_statuses(self):
    """
    主动同步退款状态：查询微信退款状态，补齐遗漏的退款回调。
    扫描所有活跃租户的 processing 状态退款记录，向微信确认实际退款状态。
    """
    logger.info("开始退款状态主动同步...")

    try:
        db_gen = get_sync_db()
        db = next(db_gen)
        try:
            # 查询所有活跃租户
            tenants = db.execute(
                select(Tenant.id).where(Tenant.status == 1)
            ).scalars().all()

            threshold = datetime.now() - timedelta(minutes=REFUND_SYNC_THRESHOLD_MINUTES)

            total_synced = 0

            for tenant_id in tenants:
                try:
                    set_tenant_context(tenant_id)
                    synced = _sync_tenant_refunds(db, tenant_id, threshold)
                    total_synced += synced
                except Exception as e:
                    logger.error(f"租户 {tenant_id} 退款状态同步失败: {e}", exc_info=True)
                finally:
                    clear_tenant_context()

            logger.info(f"退款状态主动同步完成，共更新 {total_synced} 条退款记录")

        finally:
            db_gen.close()

    except Exception as exc:
        logger.error(f"退款状态主动同步任务失败: {exc}", exc_info=True)
        raise self.retry(exc=exc)


def _sync_tenant_refunds(
    db, tenant_id: str, threshold: datetime
) -> int:
    """同步单个租户的退款状态。"""
    from app.infrastructure.payments.wechat_pay_service import WeChatPayService
    from app.modules.refunds.service import RefundService

    # 查找需要同步的退款记录
    refund_records = db.execute(
        select(RefundRecord)
        .options(
            selectinload(RefundRecord.payment_profile),
        )
        .where(
            RefundRecord.tenant_id == tenant_id,
            RefundRecord.status == "processing",
            RefundRecord.updated_at < threshold,
        )
    ).scalars().all()

    synced = 0

    for refund_record in refund_records:
        try:
            payment_profile = refund_record.payment_profile
            if not payment_profile:
                logger.warning(
                    f"退款记录 {refund_record.refund_no} 缺少支付配置，跳过"
                )
                continue

            # 调用微信退款查询接口
            wxpay_service = WeChatPayService(payment_profile=payment_profile)
            refund_info = wxpay_service.query_refund(refund_record.refund_no)

            if not refund_info:
                logger.warning(
                    f"查询退款失败: refund_no={refund_record.refund_no}"
                )
                continue

            # 解析微信退款状态
            # 微信返回的 refund_status_0 表示第一笔退款的状态
            refund_status = refund_info.get("refund_status_0")

            # 状态映射: SUCCESS -> success, FAILED -> failed, PROCESSING -> processing, ABNORMAL -> failed
            new_status = None
            failed_reason = None

            if refund_status == "SUCCESS":
                new_status = "success"
            elif refund_status == "FAILED":
                new_status = "failed"
            elif refund_status == "ABNORMAL":
                new_status = "failed"
                failed_reason = "退款异常"

            if new_status and new_status != refund_record.status:
                wx_refund_id = refund_info.get("refund_id_0")

                # 更新退款记录状态
                refund_record.status = new_status
                refund_record.wx_refund_id = wx_refund_id or refund_record.wx_refund_id
                refund_record.callback_at = datetime.now()
                if failed_reason:
                    refund_record.failed_reason = failed_reason

                db.flush()

                # 聚合到预约的退款状态
                refund_service = RefundService(db)
                refund_service.sync_appointment_refund_state(refund_record.appointment_id)

                logger.info(
                    f"退款状态同步成功: refund_no={refund_record.refund_no}, "
                    f"status={new_status}, wx_refund_id={wx_refund_id}"
                )
                synced += 1
            elif refund_status == "PROCESSING":
                logger.debug(
                    f"退款仍在处理中: refund_no={refund_record.refund_no}"
                )
            else:
                logger.warning(
                    f"未知退款状态: {refund_status}, refund_no={refund_record.refund_no}"
                )

        except Exception as e:
            logger.error(
                f"同步退款 {refund_record.refund_no} 失败: {e}",
                exc_info=True,
            )

    if synced > 0:
        db.commit()

    return synced
