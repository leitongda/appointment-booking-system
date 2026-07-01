"""Leave requests domain module."""
from app.modules.approval_flows.callback_registry import callback_registry
from app.modules.leave_requests.callbacks import handle_leave_request_approval
from app.modules.leave_requests.service import LeaveRequestService

__all__ = ["LeaveRequestService"]

# 业务侧自注册审批回调（依赖倒置：引擎不再反向 import 业务包）。
callback_registry.register("leave_request", handle_leave_request_approval)
