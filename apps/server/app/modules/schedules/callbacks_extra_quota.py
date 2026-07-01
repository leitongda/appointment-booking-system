"""加号申请（extra_quota）的审批引擎业务回调。

通过依赖倒置（业务侧自注册）拆解 approval_flows <-> schedules 的依赖：
本文件位于排班包内，由 ``schedules/__init__.py`` 在模块加载时把
:func:`handle_extra_quota_approval` 注册到引擎的 ``callback_registry``。
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval_flow import ApprovalInstance
from app.models.extra_quota_request import ExtraQuotaRequest
from app.models.schedule import Schedule
from app.modules.approval_flows.types import last_action_record
from app.utils.audit import set_update_audit
from app.utils.datetime import utc_now


async def handle_extra_quota_approval(
    action: str,
    instance: ApprovalInstance,
    db: AsyncSession,
) -> None:
    """审批引擎回调：根据审批动作更新加号申请状态与排班号源。

    Args:
        action: ``"on_approved"`` / ``"on_rejected"`` / ``"on_cancelled"``。
        instance: 审批实例，``instance.business_id`` 为 ExtraQuotaRequest.id。
        db: 异步数据库会话。
    """
    request = await db.get(ExtraQuotaRequest, instance.business_id)
    if not request or request.approval_status != "pending":
        return

    record = await last_action_record(db, instance.id)
    actor_id = record.approver_id if record else instance.updated_by or instance.applicant_id
    comment = record.comment if record else None

    if action == "on_approved":
        request.approval_status = "approved"
        request.approver_id = actor_id
        request.approval_remark = comment
        request.approved_at = utc_now()
        set_update_audit(request, actor_id)

        schedule = await db.get(Schedule, request.schedule_id)
        if schedule:
            schedule.extra_quota = (schedule.extra_quota or 0) + request.quantity
            schedule.sync_total_slots()
            set_update_audit(schedule, actor_id)
    elif action == "on_rejected":
        request.approval_status = "rejected"
        request.approver_id = actor_id
        request.approval_remark = comment
        request.approved_at = utc_now()
        set_update_audit(request, actor_id)
    elif action == "on_cancelled":
        request.approval_status = "cancelled"
        set_update_audit(request, actor_id)
