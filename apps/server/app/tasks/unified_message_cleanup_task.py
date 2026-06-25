"""
统一消息中心过期清理任务

自动归档/清理 90 天前的已读通知，防止表无限增长。
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import text

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.middleware.tenant_context import clear_tenant_context, set_tenant_context
from app.modules.unified_message.models import (
    READ_STATUS_ARCHIVED,
    READ_STATUS_DELETED,
    READ_STATUS_READ,
)

logger = logging.getLogger(__name__)

# 归档阈值：90 天前的已读消息
ARCHIVE_DAYS = 90
# 每批处理数量（防止长事务）
BATCH_SIZE = 5000


@celery_app.task(
    name="app.tasks.unified_message_cleanup_task.cleanup_expired_messages",
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    time_limit=1800,
    soft_time_limit=1500,
)
def cleanup_expired_messages():
    """
    清理过期的统一消息数据

    - 每天凌晨 3 点执行
    - 归档 90 天前的已读通知（READ_STATUS_READ → READ_STATUS_ARCHIVED）
    - 清理 90 天前的已删除通知（READ_STATUS_DELETED，物理删除）
    - 清理对应的 notification_groups 和 notification_deliveries（孤立记录）
    - 按租户分批处理，每批 BATCH_SIZE 条
    """
    logger.info("[定时任务] 开始执行：统一消息过期清理")

    cutoff = datetime.utcnow() - timedelta(days=ARCHIVE_DAYS)
    total_archived = 0
    total_deleted = 0
    total_groups_cleaned = 0

    with get_sync_db() as db:
        try:
            result = db.execute(
                text("SELECT id, tenant_code, name FROM tenants WHERE status IN (1, 3)")
            )
            tenants = result.fetchall()
        except Exception as e:
            logger.error(f"查询租户列表失败: {e}")
            return {"archived": 0, "deleted": 0, "groups_cleaned": 0, "reason": "查询租户失败"}

    if not tenants:
        logger.info("没有活跃租户，跳过清理")
        return {"archived": 0, "deleted": 0, "groups_cleaned": 0}

    for tenant_id, tenant_code, tenant_name in tenants:
        set_tenant_context(tenant_id, tenant_code)

        try:
            with get_sync_db() as db:
                params = {"tenant_id": tenant_id, "cutoff": cutoff, "batch_size": BATCH_SIZE}

                # 1. 清理已删除的消息（直接物理删除）
                # PostgreSQL 不支持 DELETE ... LIMIT，使用子查询
                result = db.execute(
                    text(f"""
                        DELETE FROM notification_recipients
                        WHERE id IN (
                            SELECT id FROM notification_recipients
                            WHERE tenant_id = :tenant_id
                              AND is_read = {READ_STATUS_DELETED}
                              AND created_at < :cutoff
                            LIMIT :batch_size
                        )
                    """),
                    params,
                )
                deleted_count = result.rowcount
                total_deleted += deleted_count

                # 2. 归档已读消息
                result = db.execute(
                    text(f"""
                        UPDATE notification_recipients
                        SET is_read = {READ_STATUS_ARCHIVED}
                        WHERE id IN (
                            SELECT id FROM notification_recipients
                            WHERE tenant_id = :tenant_id
                              AND is_read = {READ_STATUS_READ}
                              AND created_at < :cutoff
                            LIMIT :batch_size
                        )
                    """),
                    params,
                )
                archived_count = result.rowcount
                total_archived += archived_count

                # 3. 清理孤立的 notification_groups（没有任何 recipients 的 group）
                result = db.execute(
                    text("""
                        DELETE FROM notification_groups
                        WHERE id IN (
                            SELECT id FROM notification_groups
                            WHERE tenant_id = :tenant_id
                              AND created_at < :cutoff
                              AND id NOT IN (
                                  SELECT DISTINCT group_id FROM notification_recipients
                                  WHERE group_id IS NOT NULL
                              )
                            LIMIT :batch_size
                        )
                    """),
                    params,
                )
                groups_cleaned = result.rowcount
                total_groups_cleaned += groups_cleaned

                # 4. 清理孤立的 notification_deliveries（没有对应 recipient 的 delivery）
                db.execute(
                    text("""
                        DELETE FROM notification_deliveries
                        WHERE id IN (
                            SELECT id FROM notification_deliveries
                            WHERE tenant_id = :tenant_id
                              AND created_at < :cutoff
                              AND recipient_id NOT IN (
                                  SELECT id FROM notification_recipients
                              )
                            LIMIT :batch_size
                        )
                    """),
                    params,
                )

                if deleted_count or archived_count or groups_cleaned:
                    logger.info(
                        f"租户 {tenant_name} 清理完成: "
                        f"已删除={deleted_count}, 已归档={archived_count}, "
                        f"孤立组={groups_cleaned}"
                    )

        except Exception as e:
            logger.error(f"租户 {tenant_name} 清理任务执行失败: {e}")
        finally:
            clear_tenant_context()

    logger.info(
        f"[定时任务] 过期清理完成: 已归档={total_archived}, "
        f"已删除={total_deleted}, 孤立组清理={total_groups_cleaned}"
    )

    return {
        "archived": total_archived,
        "deleted": total_deleted,
        "groups_cleaned": total_groups_cleaned,
    }
