"""随访定时任务"""
import asyncio
import logging
from datetime import date, timedelta

from sqlalchemy import and_, select

from app.celery_app import celery_app
from app.db.session import get_async_db_context, get_sync_db
from app.models.follow_up_task import FollowUpTask
from app.models.message import Message, MessageType
from app.models.user import Patient

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.follow_up_task.mark_overdue_task",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=300,
    soft_time_limit=240,
)
def mark_overdue_task():
    """标记逾期随访任务（每天执行）"""
    logger.info("[定时任务] 开始标记逾期随访任务")

    async def _run():
        async for db in get_async_db_context():
            from app.modules.follow_up.service import FollowUpTaskService
            service = FollowUpTaskService(db)
            count = await service.mark_overdue()
            logger.info(f"[定时任务] 标记逾期随访任务完成，共 {count} 条")
            return count

    count = asyncio.run(_run())
    return {"overdue_count": count}


@celery_app.task(
    name="app.tasks.follow_up_task.send_follow_up_reminders",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=300,
    soft_time_limit=240,
)
def send_follow_up_reminders():
    """随访任务到期提醒（每天早上 8 点执行，提醒明天到期的 pending 任务）"""
    logger.info("[定时任务] 开始发送随访任务提醒")
    tomorrow = date.today() + timedelta(days=1)

    with get_sync_db() as db:
        # 查询明天到期且状态为 pending 的任务
        tasks = db.execute(
            select(FollowUpTask).where(
                and_(
                    FollowUpTask.status == "pending",
                    FollowUpTask.scheduled_date == tomorrow,
                    FollowUpTask.deleted_at.is_(None),
                )
            )
        ).scalars().all()

        if not tasks:
            logger.info("[定时任务] 无明天到期的随访任务")
            return {"reminder_count": 0}

        count = 0
        for task in tasks:
            # 获取患者姓名
            patient = db.get(Patient, task.patient_id)
            patient_name = patient.name if patient else "未知患者"

            message = Message(
                id=str(__import__("uuid").uuid4()),
                tenant_id=task.tenant_id,
                user_id=task.doctor_id,
                user_type="doctor",
                title="随访任务提醒",
                content=f"您有一个随访任务将于明天到期（患者：{patient_name}，编号：{task.task_no}），请及时处理。",
                message_type=MessageType.FOLLOW_UP.value,
                related_id=task.id,
                is_read=0,
            )
            db.add(message)
            count += 1

        db.commit()
        logger.info(f"[定时任务] 随访任务提醒发送完成，共 {count} 条")
        return {"reminder_count": count}
