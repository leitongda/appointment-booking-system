from sqlalchemy import Column, String, Integer, Date, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base, AuditMixin
import uuid


class ScheduleSuspension(Base, AuditMixin):
    """停诊记录模型"""
    __tablename__ = "schedule_suspensions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 租户关联（多租户支持）
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False, comment="门店ID")
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False, comment="医生ID")
    title = Column(String(100), nullable=False, comment="停诊标题")
    suspension_date = Column(Date, nullable=False, comment="停诊日期")
    schedule_ids = Column(Text, comment="选中的排班ID,JSON数组")
    time_slots = Column(Text, comment="选中的时段,JSON数组,如['08:30-12:00','13:30-17:30']")
    status = Column(Integer, default=1, comment="状态: 0已取消 1生效中")

    # 关联关系
    tenant = relationship("Tenant", back_populates="schedule_suspensions")
    store = relationship("Store", backref="schedule_suspensions")
    doctor = relationship("Doctor", backref="schedule_suspensions")
