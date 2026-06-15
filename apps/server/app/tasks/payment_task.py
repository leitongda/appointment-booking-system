"""
支付超时自动取消任务。
- 每 5 分钟扫描 status=0（待支付）且创建超过 30 分钟的预约
- 自动取消并释放号源
- 支持多租户隔离
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, update

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.middleware.tenant_context import clear_tenant_context, set_tenant_context
from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.tenant import Tenant
from app.modules.appointments.common import APPOINTMENT_STATUS

logger = logging.getLogger(__name__)

# 超时时间（分钟）
PAYMENT_TIMEOUT_MINUTES = 30


@celery_app.task(
    name="payment.cancel_expired_pending",
    queue="scheduled",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=300,
    soft_time_limit=240,
)
def cancel_expired_pending_appointments(self):
    """
    取消超时未支付的预约。
    扫描所有活跃租户的待支付预约，超时 30 分钟未支付的自动取消。
    """
    logger.info("开始扫描超时未支付预约...")

    try:
        db_gen = get_sync_db()
        db = next(db_gen)
        try:
            # 查询所有活跃租户
            tenants = db.execute(
                select(Tenant.id).where(Tenant.status == 1)
            ).scalars().all()

            timeout_threshold = datetime.now() - timedelta(minutes=PAYMENT_TIMEOUT_MINUTES)
            total_cancelled = 0

            for tenant_id in tenants:
                try:
                    set_tenant_context(tenant_id)
                    cancelled = _cancel_tenant_expired(db, tenant_id, timeout_threshold)
                    total_cancelled += cancelled
                except Exception as e:
                    logger.error(f"租户 {tenant_id} 取消超时预约失败: {e}")
                finally:
                    clear_tenant_context()

            logger.info(f"超时未支付预约扫描完成，共取消 {total_cancelled} 条预约")

        finally:
            db_gen.close()

    except Exception as exc:
        logger.error(f"取消超时未支付预约任务失败: {exc}")
        raise self.retry(exc=exc)


def _cancel_tenant_expired(db, tenant_id: str, timeout_threshold: datetime) -> int:
    """取消单个租户的超时预约。"""
    # 查找超时的待支付预约
    expired_appointments = db.execute(
        select(Appointment).where(
            Appointment.tenant_id == tenant_id,
            Appointment.status == 0,  # 待支付
            Appointment.created_at < timeout_threshold,
        )
    ).scalars().all()

    cancelled = 0
    for appointment in expired_appointments:
        try:
            update_result = db.execute(
                update(Appointment)
                .where(
                    Appointment.id == appointment.id,
                    Appointment.status == 0,
                )
                .values(
                    status=APPOINTMENT_STATUS["EXPIRED"],
                    cancel_time=datetime.now(),
                    cancel_reason="支付超时自动取消",
                )
            )
            if not update_result.rowcount:
                logger.info(
                    "预约在超时处理前已被其他流程更新，跳过过期: "
                    f"appointment_no={appointment.appointment_no}, appointment_id={appointment.id}"
                )
                continue

            # 释放号源（恢复排班已预约数量），仅在真正过期成功后执行一次。
            if appointment.schedule_id:
                db.execute(
                    update(Schedule)
                    .where(
                        Schedule.id == appointment.schedule_id,
                        Schedule.booked_slots > 0,
                    )
                    .values(booked_slots=Schedule.booked_slots - 1)
                )

            cancelled += 1
            logger.info(
                f"预约 {appointment.appointment_no} 支付超时已自动取消"
            )

        except Exception as e:
            logger.error(
                f"取消预约 {appointment.appointment_no} 失败: {e}"
            )

    if cancelled > 0:
        db.commit()

    return cancelled
