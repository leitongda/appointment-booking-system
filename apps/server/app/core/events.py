"""
业务事件类型定义与邮件钩子分发

提供轻量级的事件分发机制：业务代码调用 dispatch_event_email()，
内部通过 Celery task.delay() 投递到异步队列，不阻塞主流程。
"""
import logging
from typing import Any

from app.enums.core import EventType  # noqa: F401 — re-export

logger = logging.getLogger(__name__)


# 事件类型中文描述映射
EVENT_TYPE_LABELS: dict[str, str] = {
    EventType.APPOINTMENT_CREATED: "新预约",
    EventType.APPOINTMENT_CANCELLED: "预约取消",
    EventType.CHECKIN: "患者签到",
    EventType.CALL_PATIENT: "叫号",
    EventType.VISIT_COMPLETED: "就诊完成",
    EventType.NO_SHOW: "爽约",
    EventType.SCHEDULE_SUSPENDED: "停诊",
}


def dispatch_appointment_event(
    tenant_id: str | None,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    """
    分发预约业务事件（fire-and-forget）

    通过 Celery 异步任务驱动预约事件的副作用（如候补自动递补），
    不阻塞调用方主流程，投递失败仅记录日志。

    采用 ``celery_app.send_task(name, ...)`` 按任务名投递，而非 import 任务模块，
    以避免 ``app.core`` 静态依赖 ``app.modules``（违反 importlinter 的
    core-no-modules-dep / core-no-common-dep 契约）。任务实现模块由 Celery
    autodiscover 注册，运行期通过名字解析。

    payload 只携带可序列化的标量数据（schedule_id / appointment_id /
    tenant_id / reason），禁止传入 ORM 对象，避免跨进程引用与序列化失败。

    Args:
        tenant_id: 租户ID（落入任务上下文 ContextVar）
        event_type: 事件类型（EventType 枚举值，用于日志）
        payload: 事件载荷（必须含 schedule_id；appointment_id/reason 可选）
    """
    try:
        from app.celery_app import celery_app

        # 注入 tenant_id 到 payload，供 task 还原租户上下文
        task_payload = {
            "tenant_id": tenant_id,
            "schedule_id": payload.get("schedule_id"),
            "appointment_id": payload.get("appointment_id"),
            "reason": payload.get("reason", "APPOINTMENT_CANCELLED"),
        }
        celery_app.send_task(
            "app.tasks.waitlist_promotion_task.handle_appointment_cancelled",
            kwargs={"payload": task_payload},
        )
        logger.info(
            f"[EventDispatch] 已投递预约事件: event={event_type}, "
            f"tenant={tenant_id}, schedule={task_payload.get('schedule_id')}"
        )
    except Exception as e:
        # 投递失败不影响业务主流程（取消仍成功）
        logger.warning(
            f"[EventDispatch] 预约事件投递失败: event={event_type}, "
            f"tenant={tenant_id}, error={e}"
        )


def dispatch_event_email(
    store_id: str,
    event_type: str,
    context: dict[str, Any],
    store_name: str | None = None,
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
