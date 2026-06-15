"""
租户用量统计定时任务

- 每日统计各租户的用量数据
- 订阅到期提醒
- 用量限制警告
- 欠费自动暂停
"""
import logging
from datetime import date, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.common.sync_account_helper import count_tenant_accounts
from app.db.session import get_sync_db
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.store import Store
from app.models.tenant import Tenant, TenantUsageLog
from app.models.user import Patient

logger = logging.getLogger(__name__)


def _count_appointments(db: Session, tenant_id: str, start: datetime, end: datetime) -> int:
    """统计租户在指定时间范围内的预约数"""
    return db.scalar(
        select(func.count(Appointment.id))
        .join(Store, Appointment.store_id == Store.id)
        .where(
            and_(
                Store.tenant_id == tenant_id,
                Appointment.created_at >= start,
                Appointment.created_at <= end
            )
        )
    ) or 0


def _count_new_users(db: Session, tenant_id: str, start: datetime, end: datetime) -> int:
    """统计租户在指定时间范围内的新用户数"""
    return db.scalar(
        select(func.count(Patient.id))
        .join(Store, Patient.first_visit_store_id == Store.id)
        .where(
            and_(
                Store.tenant_id == tenant_id,
                Patient.created_at >= start,
                Patient.created_at <= end
            )
        )
    ) or 0


def _count_active_doctors(db: Session, tenant_id: str) -> int:
    """统计租户的活跃医生数"""
    return db.scalar(
        select(func.count(Doctor.id))
        .join(Store, Doctor.store_id == Store.id)
        .where(
            and_(
                Store.tenant_id == tenant_id,
                Doctor.status == 1
            )
        )
    ) or 0


@celery_app.task(
    name="app.tasks.tenant_usage_task.record_daily_usage",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=600,
    soft_time_limit=480,
)
def record_daily_usage():
    """
    记录每日租户用量（每天凌晨执行）

    统计每个租户的：
    - 预约数
    - 新用户数
    - 活跃医生数
    """
    logger.info("[定时任务] 开始记录每日租户用量")

    yesterday = date.today() - timedelta(days=1)
    day_start = datetime.combine(yesterday, datetime.min.time())
    day_end = datetime.combine(yesterday, datetime.max.time())

    with get_sync_db() as db:
        try:
            # 获取所有活跃租户
            result = db.execute(
                select(Tenant).where(Tenant.status.in_([1, 3]))  # 正常或试用
            )
            tenants = result.scalars().all()

            recorded_count = 0

            for tenant in tenants:
                try:
                    # 检查是否已有记录
                    existing = db.scalar(
                        select(TenantUsageLog).where(
                            and_(
                                TenantUsageLog.tenant_id == tenant.id,
                                TenantUsageLog.usage_date == yesterday
                            )
                        )
                    )

                    if existing:
                        log = existing
                    else:
                        log = TenantUsageLog(
                            tenant_id=tenant.id,
                            usage_date=yesterday
                        )
                        db.add(log)

                    # 统计预约数
                    log.appointment_count = _count_appointments(
                        db, tenant.id, day_start, day_end
                    )

                    # 统计新用户数
                    log.new_user_count = _count_new_users(
                        db, tenant.id, day_start, day_end
                    )

                    # 统计活跃医生数
                    log.active_doctor_count = _count_active_doctors(db, tenant.id)

                    db.commit()
                    recorded_count += 1

                except Exception as e:
                    logger.error(f"记录租户 {tenant.id} 用量失败: {e}")
                    db.rollback()
                    continue

            logger.info(f"[定时任务] 租户用量记录完成，共记录 {recorded_count} 个租户")
            return {"recorded_count": recorded_count}

        except Exception as e:
            logger.error(f"[定时任务] 租户用量记录失败: {e}")
            raise


@celery_app.task(
    name="app.tasks.tenant_usage_task.check_subscription_expiry",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=600,
    soft_time_limit=480,
)
def check_subscription_expiry():
    """
    检查订阅到期（每天执行）

    - 提前7天/3天/1天发送到期提醒
    - 到期后自动标记为欠费状态
    - 发送站内信通知
    """
    logger.info("[定时任务] 开始检查订阅到期")

    now = datetime.utcnow()
    remind_before = now + timedelta(days=7)  # 提前7天提醒

    with get_sync_db() as db:
        try:
            # 导入异步通知服务（在同步上下文中需要特殊处理）
            from app.db.session import get_async_db_context
            from app.infrastructure.notifications.service import TenantNotificationService

            # 查找所有活跃租户，检查是否需要发送通知
            result = db.execute(
                select(Tenant).where(
                    and_(
                        Tenant.status.in_([1, 3]),  # 正常或试用
                        Tenant.subscription_end_at != None,
                    )
                )
            )
            all_tenants = result.scalars().all()

            reminded_count = 0
            suspended_count = 0

            # 使用异步上下文发送通知
            async def send_notifications():
                async for db_async in get_async_db_context():
                    notification_service = TenantNotificationService(db_async)
                    for tenant in all_tenants:
                        try:
                            # 检查并发送到期提醒
                            notification = await notification_service.check_subscription_expiry(tenant.id)
                            if notification:
                                reminded_count += 1
                                logger.info(
                                    f"租户 {tenant.name}({tenant.tenant_code}) "
                                    f"将于 {tenant.subscription_end_at} 到期，已发送提醒"
                                )

                            # 如果已到期，标记为欠费
                            if tenant.subscription_end_at <= now and tenant.status == 1:
                                tenant.status = 2  # 欠费状态
                                # 发送欠费通知
                                await notification_service.send_overdue_notification(tenant.id)
                                logger.info(f"租户 {tenant.name}({tenant.tenant_code}) 已到期，标记为欠费")
                                suspended_count += 1

                        except Exception as e:
                            logger.error(f"处理租户 {tenant.id} 通知失败: {e}")
                            continue

            # 运行异步任务
            import asyncio
            asyncio.run(send_notifications())

            db.commit()

            logger.info(f"[定时任务] 订阅到期检查完成，提醒 {reminded_count} 个，暂停 {suspended_count} 个")
            return {
                "reminded_count": reminded_count,
                "suspended_count": suspended_count
            }

        except Exception as e:
            db.rollback()
            logger.error(f"[定时任务] 订阅到期检查失败: {e}")
            raise


@celery_app.task(
    name="app.tasks.tenant_usage_task.check_usage_limits",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=600,
    soft_time_limit=480,
)
def check_usage_limits():
    """
    检查用量限制（每天执行）

    当使用量接近配额时发送警告：
    - 80%：普通警告
    - 90%：重要警告
    - 100%：紧急警告
    """
    logger.info("[定时任务] 开始检查用量限制")

    with get_sync_db() as db:
        try:
            # 获取所有活跃租户
            result = db.execute(
                select(Tenant).where(Tenant.status == 1)
            )
            tenants = result.scalars().all()

            # 导入异步通知服务
            from app.db.session import get_async_db_context
            from app.infrastructure.notifications.service import TenantNotificationService

            total_warnings = 0

            # 使用异步上下文发送通知
            async def send_notifications():
                nonlocal total_warnings
                async for db_async in get_async_db_context():
                    notification_service = TenantNotificationService(db_async)
                    for tenant in tenants:
                        try:
                            # 检查并发送用量警告
                            notifications = await notification_service.check_usage_limits(tenant.id)
                            if notifications:
                                total_warnings += len(notifications)
                                for notification in notifications:
                                    logger.warning(
                                        f"租户 {tenant.name}({tenant.tenant_code}) "
                                        f"用量警告: {notification.title}"
                                    )
                        except Exception as e:
                            logger.error(f"处理租户 {tenant.id} 用量检查失败: {e}")
                            continue

            # 运行异步任务
            import asyncio
            asyncio.run(send_notifications())

            logger.info(f"[定时任务] 用量限制检查完成，发现 {total_warnings} 个警告")
            return {"warning_count": total_warnings}

        except Exception as e:
            logger.error(f"[定时任务] 用量限制检查失败: {e}")
            raise


@celery_app.task(
    name="app.tasks.tenant_usage_task.get_tenant_usage_summary",
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=180,
    soft_time_limit=150,
)
def get_tenant_usage_summary(tenant_id: str):
    """
    获取租户用量汇总（按需调用）

    Args:
        tenant_id: 租户ID

    Returns:
        用量汇总数据
    """
    with get_sync_db() as db:
        tenant = db.get(Tenant, tenant_id)
        if not tenant:
            return None

        # 获取当前使用量
        store_count = db.scalar(
            select(func.count(Store.id)).where(Store.tenant_id == tenant_id)
        ) or 0

        # 尝试从 Account 表统计，无数据则 fallback 到旧表
        # count_tenant_accounts 内部已实现 Account 优先 + 旧表 fallback 策略
        account_counts = count_tenant_accounts(db, tenant_id)
        admin_count = account_counts["admin_count"]
        doctor_count = account_counts["doctor_count"]

        # 本月预约数
        month_start = date.today().replace(day=1)
        month_appointments = db.scalar(
            select(func.count(Appointment.id))
            .join(Store, Appointment.store_id == Store.id)
            .where(
                and_(
                    Store.tenant_id == tenant_id,
                    Appointment.created_at >= month_start
                )
            )
        ) or 0

        # 配额
        max_stores = tenant.get_effective_max_stores()
        max_admins = tenant.get_effective_max_admins()
        max_doctors = tenant.get_effective_max_doctors()
        max_appointments = tenant.get_effective_max_appointments()

        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant.name,
            "max_stores": max_stores,
            "max_admins": max_admins,
            "max_doctors": max_doctors,
            "max_appointments_per_month": max_appointments,
            "current_store_count": store_count,
            "current_admin_count": admin_count,
            "current_doctor_count": doctor_count,
            "current_month_appointments": month_appointments,
            "store_usage_rate": round(store_count / max_stores * 100, 2) if max_stores > 0 else 0,
            "admin_usage_rate": round(admin_count / max_admins * 100, 2) if max_admins > 0 else 0,
            "doctor_usage_rate": round(doctor_count / max_doctors * 100, 2) if max_doctors > 0 else 0,
            "appointment_usage_rate": round(month_appointments / max_appointments * 100, 2) if max_appointments > 0 else 0,
        }
