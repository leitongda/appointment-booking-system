"""
候补自动递补异步任务（事件驱动）

当预约被取消释放号源时，预约模块通过
``app.core.events.dispatch_appointment_event`` 投递
``APPOINTMENT_CANCELLED`` 事件，由本任务异步触发候补队列自动递补。

设计要点：
- 打破 ``modules/appointments`` 与 ``modules/waitlist`` 的循环依赖：
  方向 B（appointments → waitlist）由同步调用改为 Celery 事件。
- 失败不重试：与历史行为一致（递补失败不影响取消主流程），
  失败可见性从 cancel 调用栈的 logger.warning 迁移到此处 logger.error。
- 不传 ORM 对象：payload 仅携带可序列化标量。
- WaitlistService.auto_promote 是 async 方法（依赖 AsyncSession + async 的
  AppointmentService.create），因此通过 ``async_session_maker`` +
  ``loop.run_until_complete`` 桥接到同步 Celery worker（与
  ``notification_task`` 同款范式），而不是用 sync session。
"""
import asyncio
import logging
from typing import Any

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.waitlist_promotion_task.handle_appointment_cancelled",
    bind=True,
    autoretry_for=(),
    max_retries=0,
    time_limit=120,
    soft_time_limit=90,
)
def handle_appointment_cancelled(self, payload: dict[str, Any]) -> dict[str, Any]:
    """处理预约取消事件 —— 触发候补队列自动递补。

    Args:
        payload: {
            tenant_id: str | None,
            schedule_id: str,
            appointment_id: str | None,
            reason: str,  # 默认 "APPOINTMENT_CANCELLED"
        }

    Returns:
        结果摘要字典（供 Flower / 日志观测）。

    异常策略:
        全程 try/except：任何异常仅 logger.error，不外抛、不重试，
        与"递补失败不影响取消"的历史语义保持一致。
    """
    tenant_id = payload.get("tenant_id")
    schedule_id = payload.get("schedule_id")
    appointment_id = payload.get("appointment_id")
    reason = payload.get("reason") or "APPOINTMENT_CANCELLED"

    if not schedule_id:
        logger.error(
            "[WaitlistPromotion] payload 缺少 schedule_id，跳过递补: payload=%s",
            payload,
        )
        return {"ok": False, "reason": "missing_schedule_id"}

    try:
        # 1) 还原租户上下文（ContextVar）—— auto_promote 内部按租户隔离
        from app.middleware.tenant_context import set_tenant_context

        set_tenant_context(tenant_id)

        # 2) 通过 async session 桥接运行 WaitlistService.auto_promote
        from app.db.session import async_session_maker
        from app.modules.waitlist.service import WaitlistService

        async def _run() -> int:
            async with async_session_maker() as session:
                service = WaitlistService(session)
                promoted = await service.auto_promote(
                    schedule_id=schedule_id,
                    reason=reason,
                )
                return len(promoted or [])

        loop = asyncio.new_event_loop()
        try:
            promoted_count = loop.run_until_complete(_run())
        finally:
            loop.close()

        logger.info(
            "[WaitlistPromotion] 递补完成: tenant=%s schedule=%s "
            "appointment=%s promoted=%s",
            tenant_id,
            schedule_id,
            appointment_id,
            promoted_count,
        )
        return {
            "ok": True,
            "tenant_id": tenant_id,
            "schedule_id": schedule_id,
            "appointment_id": appointment_id,
            "promoted_count": promoted_count,
        }
    except Exception as e:  # noqa: BLE001 — 递补失败需吞掉，不影响取消
        # 失败不重试、不外抛（与"递补失败不影响取消"的历史语义一致）
        logger.error(
            "[WaitlistPromotion] 候补自动递补失败: tenant=%s schedule=%s "
            "appointment=%s error=%s",
            tenant_id,
            schedule_id,
            appointment_id,
            e,
            exc_info=True,
        )
        return {
            "ok": False,
            "tenant_id": tenant_id,
            "schedule_id": schedule_id,
            "appointment_id": appointment_id,
            "error": str(e),
        }
