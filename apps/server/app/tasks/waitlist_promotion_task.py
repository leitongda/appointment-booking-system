"""
候补自动递补异步任务（事件驱动）

当预约被取消释放号源时，预约模块通过
``app.core.events.dispatch_appointment_event`` 投递
``APPOINTMENT_CANCELLED`` 事件，由本任务异步触发候补队列自动递补。

设计要点：
- 打破 ``modules/appointments`` 与 ``modules/waitlist`` 的循环依赖：
  方向 B（appointments → waitlist）由同步调用改为 Celery 事件。
- 瞬时故障（DB 抖动、锁冲突）指数退避重试 3 次；用尽后放弃（取消主流程已成功），
  由 ``reconcile_stuck_promotions`` 周期告警兜底"号源空转"风险。
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
    max_retries=3,
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
        瞬时故障（DB 抖动、锁冲突）指数退避重试 3 次（count=2^retries）；
        用尽后仅 logger.error，不外抛 —— 取消主流程已成功，号源空转由
        ``reconcile_stuck_promotions`` 周期告警兜底。
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
        # 瞬时故障（DB 抖动、锁冲突）指数退避重试；用尽后放弃（取消已成功，
        # 号源空转由 reconcile_stuck_promotions 周期告警兜底）。
        if self.request.retries < self.max_retries:
            logger.warning(
                "[WaitlistPromotion] 递补失败，将重试 %d/%d: tenant=%s "
                "schedule=%s appointment=%s error=%s",
                self.request.retries + 1,
                self.max_retries,
                tenant_id,
                schedule_id,
                appointment_id,
                e,
            )
            raise self.retry(exc=e, countdown=2 ** self.request.retries) from None
        logger.error(
            "[WaitlistPromotion] 候补递补重试 %d 次仍失败，放弃（号源已释放，"
            "需核查 reconcile 告警）: tenant=%s schedule=%s appointment=%s error=%s",
            self.max_retries,
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
            "exhausted_retries": True,
        }


@celery_app.task(
    name="app.tasks.waitlist_promotion_task.reconcile_stuck_promotions",
    time_limit=60,
    soft_time_limit=45,
)
def reconcile_stuck_promotions() -> dict[str, Any]:
    """周期性探测卡在 PROCESSING 的候补（递补 task 异常崩溃未回退的异常态）。

    PROCESSING 是 ``WaitlistService.auto_promote`` 内部的瞬态（毫秒级
    set→resolve 为 PROMOTED/WAITING）。若被周期任务观测到，几乎必然是
    递补 task 在 set PROCESSING 后、resolve 前崩溃（worker kill / OOM /
    异常未捕获路径），status 未回退 WAITING。

    本任务**仅告警**（结构化 error 日志，便于 Flower/日志系统告警），**不自动
    重置/重投** —— 避免误判正常在途递补（虽概率极低）。运营据此决定是否人工
    介入；自动重投/outbox 补偿属后续可靠性增强。
    """
    try:
        from sqlalchemy import select

        from app.db.session import get_sync_db
        from app.models.waitlist import WaitlistEntry

        db_gen = get_sync_db()
        db = next(db_gen)
        try:
            stuck = db.execute(
                select(
                    WaitlistEntry.id,
                    WaitlistEntry.schedule_id,
                    WaitlistEntry.tenant_id,
                ).where(WaitlistEntry.status == "PROCESSING")
            ).all()
        finally:
            db_gen.close()

        if stuck:
            logger.error(
                "[WaitlistPromotionReconcile] 检测到 %d 条候补卡在 PROCESSING"
                "（递补 task 异常未回退，核查号源是否空转）: entries=%s",
                len(stuck),
                [(row.id, row.schedule_id, str(row.tenant_id)) for row in stuck],
            )
            return {"stuck_count": len(stuck), "ids": [row.id for row in stuck]}
        return {"stuck_count": 0}
    except Exception as e:  # noqa: BLE001 — 探测失败不应中断 beat 调度
        logger.error(
            "[WaitlistPromotionReconcile] 探测失败: %s", e, exc_info=True
        )
        return {"ok": False, "error": str(e)}
