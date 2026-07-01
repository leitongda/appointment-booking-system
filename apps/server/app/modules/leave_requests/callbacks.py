"""停诊/调班申请的审批引擎业务回调。

通过依赖倒置（业务侧自注册）拆解 approval_flows <-> leave_requests 的循环依赖：
本文件位于业务包内，可直接 import 同包的 :class:`LeaveRequestService`，
由 ``leave_requests/__init__.py`` 在模块加载时把
:func:`handle_leave_request_approval` 注册到引擎的 ``callback_registry``。
"""
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval_flow import ApprovalInstance
from app.models.leave_request import LeaveRequest, RequestStatus
from app.modules.approval_flows.types import last_action_record
from app.modules.leave_requests.service import LeaveRequestService
from app.utils.audit import set_update_audit


async def handle_leave_request_approval(
    action: str,
    instance: ApprovalInstance,
    db: AsyncSession,
) -> None:
    """审批引擎回调：根据审批动作更新停诊/调班申请状态。

    Args:
        action: ``"on_approved"`` / ``"on_rejected"`` / ``"on_cancelled"``。
        instance: 审批实例，``instance.business_id`` 为 LeaveRequest.id。
        db: 异步数据库会话。
    """
    request = await db.get(LeaveRequest, instance.business_id)
    if not request or request.status != RequestStatus.PENDING.value:
        return

    record = await last_action_record(db, instance.id)
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
