"""
登录历史清理定时任务
- 清理超过保留天数的管理员登录历史记录
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import delete

from app.celery_app import celery_app
from app.core.config import settings
from app.db.session import get_sync_db
from app.models.admin import AdminLoginHistory

logger = logging.getLogger(__name__)


@celery_app.task(
    name="cleanup_login_history",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=300,
    soft_time_limit=240,
)
def cleanup_login_history():
    """
    清理过期的管理员登录历史记录

    删除 login_time 早于 LOGIN_HISTORY_RETENTION_DAYS 天前的记录。
    每天凌晨 3 点由 Celery beat 调度执行。
    """
    retention_days = settings.LOGIN_HISTORY_RETENTION_DAYS
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    logger.info(
        f"[定时任务] 开始清理登录历史: 保留 {retention_days} 天, "
        f"删除 {cutoff_date.strftime('%Y-%m-%d')} 之前的记录"
    )

    with get_sync_db() as db:
        try:
            result = db.execute(
                delete(AdminLoginHistory).where(
                    AdminLoginHistory.login_time < cutoff_date
                )
            )
            cleaned = result.rowcount
            db.commit()

            logger.info(
                f"[定时任务] 登录历史清理完成: 删除 {cleaned} 条记录"
            )
            return {"cleaned": cleaned, "retention_days": retention_days}

        except Exception as e:
            db.rollback()
            logger.error(f"[定时任务] 登录历史清理失败: {e}")
            raise
