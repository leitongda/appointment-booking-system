from sqlalchemy import Column, String, Integer, Text, Date, DateTime, ForeignKey
from app.db.base import Base, AuditMixin
import uuid
import enum


class RequestType(str, enum.Enum):
    """申请类型"""
    STOP_CLINIC = "stop_clinic"  # 停诊申请
    SCHEDULE_CHANGE = "schedule_change"  # 调班申请


class RequestStatus(str, enum.Enum):
    """申请状态"""
    PENDING = "pending"  # 待审核
    APPROVED = "approved"  # 已通过
    REJECTED = "rejected"  # 已拒绝
    CANCELLED = "cancelled"  # 已取消


class LeaveRequest(Base, AuditMixin):
    """停诊/调班申请模型"""
    __tablename__ = "leave_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    doctor_id = Column(String(36), nullable=False, index=True, comment="医生ID")
    request_type = Column(String(20), nullable=False, comment="申请类型: stop_clinic/schedule_change")
    
    # 停诊信息
    schedule_id = Column(String(36), comment="排班ID（停诊时）")
    stop_date = Column(Date, comment="停诊日期")
    stop_period = Column(String(20), comment="停诊时段: morning/afternoon/evening/all")
    
    # 调班信息
    original_date = Column(Date, comment="原日期（调班时）")
    original_period = Column(String(20), comment="原时段")
    target_date = Column(Date, comment="目标日期")
    target_period = Column(String(20), comment="目标时段")
    
    # 申请信息
    reason = Column(Text, nullable=False, comment="申请原因")
    status = Column(String(20), default=RequestStatus.PENDING.value, comment="状态")
    
    # 审核信息
    reviewer_id = Column(String(36), comment="审核人ID")
    review_comment = Column(Text, comment="审核意见")
    reviewed_at = Column(DateTime, comment="审核时间")
    
    # 受影响的预约数
    affected_appointments = Column(Integer, default=0, comment="受影响预约数")
