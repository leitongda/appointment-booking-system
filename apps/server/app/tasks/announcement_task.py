"""
平台公告定时发布任务

每分钟检查是否有到时间的定时公告需要发布。
"""

import asyncio
import logging

from app.celery_app import celery_app
from app.db.session import get_async_db_context

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.announcement_task.publish_scheduled_announcements",
    time_limit=120,
    soft_time_limit=90,
)
def publish_scheduled_announcements():
    """发布所有到时间的定时公告"""
    try:
        result = asyncio.run(_publish_scheduled())
        if result:
            logger.info("已发布 %d 条定时公告: %s", len(result), result)
    except Exception:
        logger.exception("定时公告发布任务异常")


async def _publish_scheduled() -> list[str]:
    async with get_async_db_context() as db:
        from app.modules.platform_announcements.service import PlatformAnnouncementService

        service = PlatformAnnouncementService(db)
        return await service.publish_scheduled()
