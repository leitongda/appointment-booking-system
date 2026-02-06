"""
业务事件类型定义与邮件钩子分发

提供轻量级的事件分发机制：业务代码调用 dispatch_event_email()，
内部通过 Celery task.delay() 投递到异步队列，不阻塞主流程。
"""
import logging
from enum import Enum
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """业务事件类型"""
    APPOINTMENT_CREATED = "appointment_created"       # 新预约
    APPOINTMENT_CANCELLED = "appointment_cancelled"   # 预约取消
    CHECKIN = "checkin"                               # 患者签到
    CALL_PATIENT = "call_patient"                     # 叫号
    VISIT_COMPLETED = "visit_completed"               # 就诊完成
    NO_SHOW = "no_show"                               # 爽约
    SCHEDULE_SUSPENDED = "schedule_suspended"          # 停诊


# 事件类型中文描述映射
EVENT_TYPE_LABELS: Dict[str, str] = {
    EventType.APPOINTMENT_CREATED: "新预约",
    EventType.APPOINTMENT_CANCELLED: "预约取消",
    EventType.CHECKIN: "患者签到",
    EventType.CALL_PATIENT: "叫号",
    EventType.VISIT_COMPLETED: "就诊完成",
    EventType.NO_SHOW: "爽约",
    EventType.SCHEDULE_SUSPENDED: "停诊",
}


def dispatch_event_email(
    store_id: str,
    event_type: str,
    context: Dict[str, Any],
    store_name: Optional[str] = None,
) -> None:
    """
    分发业务事件邮件通知（fire-and-forget）

    投递 Celery 异步任务，不阻塞调用方。
    发送失败仅记录日志，不影响业务主流程。

    Args:
        store_id: 门店ID
        event_type: 事件类型（EventType 枚举值）
        context: 事件上下文数据（模板变量）
        store_name: 门店名称（可选，用于日志）
    """
    try:
        from app.tasks.email_hook_task import process_event_email
        process_event_email.delay(store_id, event_type, context)
        logger.info(
            f"[EventHook] 已投递邮件事件: event={event_type}, "
            f"store={store_name or store_id}"
        )
    except Exception as e:
        # 投递失败不影响业务
        logger.warning(
            f"[EventHook] 邮件事件投递失败: event={event_type}, "
            f"store={store_name or store_id}, error={e}"
        )
