"""
通知配额检查定时任务

每日检查各租户的通知用量，达到 80% 或 100% 时发送告警。
"""
import logging

from sqlalchemy import select

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.middleware.tenant_context import clear_tenant_context, set_tenant_context
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.notification_quota_task.check_notification_quota",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=600,
    soft_time_limit=480,
)
def check_notification_quota():
    """
    检查通知配额（每日执行）

    遍历所有活跃租户，检查其通知用量：
    - 用量达到 80%：普通警告
    - 用量达到 90%：重要警告
    - 用量达到 100%：紧急警告（配额已用尽）
    """
    logger.info("[定时任务] 开始检查通知配额")

    with get_sync_db() as db:
        try:
            # 获取所有活跃租户
            result = db.execute(
                select(Tenant).where(Tenant.status.in_([1, 3]))  # 正常或试用
            )
            tenants = result.scalars().all()

            if not tenants:
                logger.info("没有活跃租户，跳过通知配额检查")
                return {"checked_count": 0, "alert_count": 0}

            logger.info(f"找到 {len(tenants)} 个活跃租户")

            # 导入异步通知服务
            from app.db.session import get_async_db_context
            from app.infrastructure.notifications.quota import NotificationQuotaService

            total_alerts = 0
            checked_count = 0

            # 使用异步上下文发送通知
            async def check_all_tenants():
                nonlocal total_alerts, checked_count
                async for db_async in get_async_db_context():
                    for tenant in tenants:
                        # 设置当前租户上下文
                        set_tenant_context(tenant.id, tenant.tenant_code)

                        try:
                            quota_service = NotificationQuotaService(db_async)
                            notifications = await quota_service.check_and_alert(tenant.id)

                            if notifications:
                                total_alerts += len(notifications)
                                for notification in notifications:
                                    channel = notification.metadata.get("channel", "unknown") if notification.metadata else "unknown"
                                    logger.warning(
                                        f"租户 {tenant.name}({tenant.tenant_code}) "
                                        f"通知配额告警: {notification.title} "
                                        f"(渠道: {channel}, 用量: {notification.metadata.get('usage_percent', 0) if notification.metadata else 0}%)"
                                    )

                            checked_count += 1

                        except Exception as e:
                            logger.error(f"检查租户 {tenant.id} 通知配额失败: {e}")
                            continue
                        finally:
                            # 清除租户上下文
                            clear_tenant_context()

            # 运行异步任务
            import asyncio
            asyncio.run(check_all_tenants())

            logger.info(f"[定时任务] 通知配额检查完成，检查 {checked_count} 个租户，发送 {total_alerts} 个告警")
            return {
                "checked_count": checked_count,
                "alert_count": total_alerts,
            }

        except Exception as e:
            logger.error(f"[定时任务] 通知配额检查失败: {e}")
            raise


@celery_app.task(
    name="app.tasks.notification_quota_task.get_tenant_notification_quota",
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=180,
    soft_time_limit=150,
)
def get_tenant_notification_quota(tenant_id: str):
    """
    获取租户通知配额汇总（按需调用）

    Args:
        tenant_id: 租户ID

    Returns:
        配额汇总数据
    """
    from app.db.session import get_async_db_context
    from app.infrastructure.notifications.quota import NotificationQuotaService

    async def get_quota():
        async for db_async in get_async_db_context():
            quota_service = NotificationQuotaService(db_async)
            return await quota_service.get_quota_info(tenant_id)

    import asyncio
    return asyncio.run(get_quota())