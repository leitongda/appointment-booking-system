"""审批相关枚举"""
from enum import Enum


class ApprovalInstanceStatus(str, Enum):
    """审批实例状态"""
    PENDING = "pending"      # 待审批
    APPROVED = "approved"    # 已批准
    REJECTED = "rejected"    # 已拒绝
    WITHDRAWN = "withdrawn"  # 已撤回
