"""停诊/调班申请服务 - 兼容层

实际实现已迁移至 app.modules.leave_requests.service
"""
from app.modules.leave_requests.service import LeaveRequestService

__all__ = ["LeaveRequestService"]
