"""
排班号源对账任务。
- 每天凌晨 3:30 执行（与排班生成错开）
- 遍历所有活跃租户，比对 schedules.booked_slots 与实际活跃预约数
- 自动修复不一致数据并记录日志
- 支持多租户隔离
"""
import logging
from datetime import date

from sqlalchemy import func, select, and_

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.middleware.tenant_context import set_tenant_context, clear_tenant_context
from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.tenant import Tenant
from app.modules.appointments.common import ACTIVE_APPOINTMENT_STATUSES

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.schedule_reconciliation_task.reconcile_booked_slots",
    queue="scheduled",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=1,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=600,
    soft_time_limit=480,
)
def reconcile_booked_slots(self):
    """
    对排班表 booked_slots 字段进行一致性校验。
    比对每个排班的 booked_slots 与该排班下活跃预约的实际 COUNT，修复不一致数据。
    """
    logger.info("开始排班号源对账任务...")

    try:
        db_gen = get_sync_db()
        db = next(db_gen)
        try:
            tenants = db.execute(
                select(Tenant.id, Tenant.tenant_code).where(Tenant.status == 1)
            ).all()

            total_checked = 0
            total_drift = 0
            total_fixed = 0

            for tenant_id, tenant_code in tenants:
                try:
                    set_tenant_context(tenant_id, tenant_code)
                    checked, drifted, fixed = _reconcile_tenant(db, tenant_id)
                    total_checked += checked
                    total_drift += drifted
                    total_fixed += fixed
                except Exception as e:
                    logger.error(f"租户 {tenant_id} 号源对账失败: {e}")
                finally:
                    clear_tenant_context()

            logger.info(
                f"排班号源对账完成: 检查 {total_checked} 条排班, "
                f"发现 {total_drift} 条偏差, 修复 {total_fixed} 条"
            )

        finally:
            db_gen.close()

    except Exception as exc:
        logger.error(f"排班号源对账任务失败: {exc}")
        raise self.retry(exc=exc)


def _reconcile_tenant(db, tenant_id: str) -> tuple[int, int, int]:
    """对单个租户进行对账，返回 (检查数, 偏差数, 修复数)。"""
    today = date.today()

    subquery = (
        select(
            Appointment.schedule_id,
            func.count(Appointment.id).label("actual_count"),
        )
        .where(
            and_(
                Appointment.tenant_id == tenant_id,
                Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
            )
        )
        .group_by(Appointment.schedule_id)
        .subquery()
    )

    rows = db.execute(
        select(
            Schedule.id,
            Schedule.booked_slots,
            func.coalesce(subquery.c.actual_count, 0).label("actual_count"),
        )
        .outerjoin(subquery, Schedule.id == subquery.c.schedule_id)
        .where(
            and_(
                Schedule.tenant_id == tenant_id,
                Schedule.schedule_date >= today,
            )
        )
    ).all()

    checked = len(rows)
    drifted = 0
    fixed = 0

    for schedule_id, booked_slots, actual_count in rows:
        if booked_slots != actual_count:
            drifted += 1
            logger.warning(
                f"号源偏差: schedule_id={schedule_id}, "
                f"booked_slots={booked_slots}, actual={actual_count}, "
                f"tenant_id={tenant_id}"
            )
            try:
                db.execute(
                    Schedule.__table__.update()
                    .where(Schedule.__table__.c.id == schedule_id)
                    .values(booked_slots=actual_count)
                )
                db.commit()
                fixed += 1
            except Exception as e:
                db.rollback()
                logger.error(f"修复号源偏差失败: schedule_id={schedule_id}, error={e}")

    if checked > 0:
        logger.info(
            f"租户 {tenant_id} 对账完成: 检查 {checked} 条, "
            f"偏差 {drifted} 条, 修复 {fixed} 条"
        )

    return checked, drifted, fixed
