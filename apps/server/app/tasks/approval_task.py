"""审批流 Celery 任务"""
import asyncio
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import and_, select

from app.celery_app import celery_app
from app.db.session import get_sync_db

logger = logging.getLogger(__name__)


def _run_async(coro):
    """在同步 Celery 任务中运行异步代码"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="app.tasks.approval_task.send_approval_notification",
    queue="notification",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    time_limit=30,
    soft_time_limit=25,
)
def send_approval_notification(user_id: str, message_type: str, data: dict[str, Any]):
    """
    发送审批通知（WebSocket）

    Args:
        user_id: 接收人 ID
        message_type: 消息类型 (approval_pending/approval_approved/approval_rejected/approval_delegated/approval_withdrawn)
        data: 消息数据
    """
    from app.core.websocket import WSMessageType, notify_doctor

    ws_type_map = {
        "approval_pending": WSMessageType.APPROVAL_PENDING,
        "approval_approved": WSMessageType.APPROVAL_APPROVED,
        "approval_rejected": WSMessageType.APPROVAL_REJECTED,
        "approval_delegated": WSMessageType.APPROVAL_DELEGATED,
        "approval_withdrawn": WSMessageType.APPROVAL_WITHDRAWN,
    }

    ws_type = ws_type_map.get(message_type)
    if not ws_type:
        logger.warning(f"未知的审批通知类型: {message_type}")
        return

    try:
        _run_async(notify_doctor(user_id, ws_type, data=data))
        logger.info(f"审批通知已发送: user={user_id}, type={message_type}")
    except Exception as e:
        logger.error(f"审批通知发送失败: user={user_id}, type={message_type}, error={e}")
        raise


@celery_app.task(
    name="app.tasks.approval_task.check_approval_timeouts",
    queue="scheduled",
    autoretry_for=(Exception,),
    max_retries=2,
    time_limit=120,
    soft_time_limit=100,
)
def check_approval_timeouts():
    """检查审批超时任务（定时执行，每 10 分钟，带分布式锁防重复）"""
    from app.core.redis import SyncRedisCache

    lock_name = "celery:check_approval_timeouts"
    lock_value = SyncRedisCache.acquire_lock(lock_name, timeout=90, retry_times=1, retry_delay=0)
    if not lock_value:
        logger.info("审批超时检查任务已在其他实例执行，跳过")
        return

    try:
        _do_check_approval_timeouts()
    finally:
        SyncRedisCache.release_lock(lock_name, lock_value)


def _do_check_approval_timeouts():
    """审批超时检查 — 实际执行逻辑"""
    from app.models.approval_flow import ApprovalFlowNode, ApprovalInstance, ApprovalTask

    with get_sync_db() as db:
        now = datetime.utcnow()

        # 查找超时的 pending 任务
        stmt = (
            select(ApprovalTask)
            .join(ApprovalInstance, ApprovalTask.instance_id == ApprovalInstance.id)
            .where(
                and_(
                    ApprovalTask.status == "pending",
                    ApprovalTask.timeout_at.isnot(None),
                    ApprovalTask.timeout_at < now,
                    ApprovalInstance.status == "pending",
                )
            )
        )
        tasks = db.execute(stmt).scalars().all()

        if not tasks:
            return

        logger.info(f"发现 {len(tasks)} 个超时审批任务")

        for task in tasks:
            instance = db.get(ApprovalInstance, task.instance_id)
            if not instance or instance.status != "pending":
                continue

            # 获取节点的超时动作配置
            node_stmt = select(ApprovalFlowNode).where(
                and_(
                    ApprovalFlowNode.flow_def_id == instance.flow_def_id,
                    ApprovalFlowNode.node_key == task.node_key,
                )
            )
            node = db.execute(node_stmt).scalar_one_or_none()
            if not node:
                continue

            timeout_action = node.timeout_action or "remind"

            if timeout_action == "remind":
                # 发送提醒通知
                send_approval_notification.delay(
                    user_id=task.assignee_id,
                    message_type="approval_pending",
                    data={
                        "instance_id": instance.id,
                        "title": instance.title,
                        "node_name": task.node_name,
                        "is_remind": True,
                        "timeout_at": task.timeout_at.isoformat() if task.timeout_at else None,
                    },
                )
                logger.info(f"超时提醒已发送: task={task.id}, assignee={task.assignee_id}")

            elif timeout_action == "auto_approve":
                # 不在这里标记任务，由引擎处理（保证事务一致性）
                logger.info(f"超时自动通过触发: task={task.id}, instance={instance.id}")
                _advance_after_auto_approve.delay(task.instance_id, task.node_key, task.assignee_id)

            elif timeout_action == "auto_reject":
                logger.info(f"超时自动拒绝触发: task={task.id}, instance={instance.id}")
                _auto_reject_after_timeout.delay(task.instance_id, task.node_key, task.assignee_id)

        db.commit()


@celery_app.task(
    name="app.tasks.approval_task.advance_after_auto_approve",
    queue="default",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    time_limit=60,
    soft_time_limit=50,
)
def _advance_after_auto_approve(instance_id: str, node_key: str, approver_id: str):
    """超时自动通过后推进引擎"""
    from app.db.session import AsyncSessionLocal
    from app.models.approval_flow import ApprovalInstance
    from app.modules.approval_flows.engine import ApprovalEngine

    async def _run():
        async with AsyncSessionLocal() as db:
            engine = ApprovalEngine(db)
            instance = db.get(ApprovalInstance, instance_id)
            if not instance or instance.status != "pending":
                return
            await engine.approve(instance_id, approver_id, "system", comment="超时自动通过")

    _run_async(_run())


@celery_app.task(
    name="app.tasks.approval_task.auto_reject_after_timeout",
    queue="default",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    time_limit=60,
    soft_time_limit=50,
)
def _auto_reject_after_timeout(instance_id: str, node_key: str, approver_id: str):
    """超时自动拒绝"""
    from app.db.session import AsyncSessionLocal
    from app.models.approval_flow import ApprovalInstance
    from app.modules.approval_flows.engine import ApprovalEngine

    async def _run():
        async with AsyncSessionLocal() as db:
            engine = ApprovalEngine(db)
            instance = db.get(ApprovalInstance, instance_id)
            if not instance or instance.status != "pending":
                return
            await engine.reject(instance_id, approver_id, "system", comment="超时自动拒绝")

    _run_async(_run())
