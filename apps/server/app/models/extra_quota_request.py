"""加号申请模型。"""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class ExtraQuotaRequest(Base, AuditMixin):
    """加号申请记录。"""

    __tablename__ = "extra_quota_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False, index=True, comment="门店ID")
    schedule_id = Column(String(36), ForeignKey("schedules.id"), nullable=False, index=True, comment="排班ID")
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False, index=True, comment="医生ID")
    schedule_date = Column(String(10), nullable=False, comment="排班日期 YYYY-MM-DD")
    time_slot = Column(String(20), nullable=False, comment="时间段: morning/afternoon/evening")
    quantity = Column(Integer, nullable=False, default=1, comment="加号数量")
    quota_type = Column(String(20), nullable=False, default="normal", comment="加号类型: normal/special/green_channel")
    open_to_public = Column(Integer, default=1, comment="是否对外开放: 1=是 0=否")
    patient_id = Column(String(36), nullable=True, comment="指定患者ID（特批加号时使用）")
    reason = Column(Text, nullable=True, comment="加号原因")
    approval_status = Column(String(20), nullable=False, default="pending", comment="审批状态: pending/approved/rejected/cancelled")
    applicant_id = Column(String(36), nullable=False, comment="申请人ID")
    approver_id = Column(String(36), nullable=True, comment="审批人ID")
    approval_remark = Column(Text, nullable=True, comment="审批备注")
    approved_at = Column(DateTime, nullable=True, comment="审批时间")

    # 关联关系（使用 backref 避免修改已有模型）
    schedule = relationship("Schedule", lazy="selectin")
    doctor = relationship("Doctor", lazy="selectin")

    __table_args__ = (
        Index("ix_extra_quota_tenant_schedule", "tenant_id", "schedule_id"),
        {"comment": "加号申请表"},
    )
