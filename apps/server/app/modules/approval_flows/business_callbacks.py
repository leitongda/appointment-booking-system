"""Built-in business callbacks for the generic approval engine."""
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval_flow import ApprovalInstance, ApprovalRecord
from app.models.extra_quota_request import ExtraQuotaRequest
from app.models.leave_request import LeaveRequest, RequestStatus
from app.models.schedule import Schedule
from app.modules.approval_flows.callback_registry import callback_registry
from app.modules.leave_requests.service import LeaveRequestService
from app.utils.audit import set_update_audit
from app.utils.datetime import utc_now


async def _last_action_record(db: AsyncSession, instance_id: str) -> Optional[ApprovalRecord]:
    result = await db.execute(
        select(ApprovalRecord)
        .where(
            and_(
                ApprovalRecord.instance_id == instance_id,
                ApprovalRecord.action.in_(["approve", "reject", "withdraw"]),
            )
        )
        .order_by(ApprovalRecord.created_at.desc())
    )
    return result.scalars().first()


async def handle_leave_request_approval(
    action: str,
    instance: ApprovalInstance,
    db: AsyncSession,
):
    request = await db.get(LeaveRequest, instance.business_id)
    if not request or request.status != RequestStatus.PENDING.value:
        return

    record = await _last_action_record(db, instance.id)
    actor_id = record.approver_id if record else instance.updated_by or instance.applicant_id
    comment = record.comment if record else None

    if action == "on_approved":
        request.status = RequestStatus.APPROVED.value
        request.reviewer_id = actor_id
        request.review_comment = comment
        request.reviewed_at = datetime.utcnow()
        set_update_audit(request, actor_id)
        await LeaveRequestService(db)._handle_approved_request(request)
    elif action == "on_rejected":
        request.status = RequestStatus.REJECTED.value
        request.reviewer_id = actor_id
        request.review_comment = comment
        request.reviewed_at = datetime.utcnow()
        set_update_audit(request, actor_id)
    elif action == "on_cancelled":
        request.status = RequestStatus.CANCELLED.value
        set_update_audit(request, actor_id)


async def handle_extra_quota_approval(
    action: str,
    instance: ApprovalInstance,
    db: AsyncSession,
):
    request = await db.get(ExtraQuotaRequest, instance.business_id)
    if not request or request.approval_status != "pending":
        return

    record = await _last_action_record(db, instance.id)
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


def register_builtin_callbacks():
    callback_registry.register("leave_request", handle_leave_request_approval)
    callback_registry.register("extra_quota", handle_extra_quota_approval)
