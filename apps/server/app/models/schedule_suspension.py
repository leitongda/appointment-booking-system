import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


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

    # 患者处置相关字段
    suspension_type = Column(
        String(20), nullable=False, default='temporary',
        comment='停诊类型: temporary/full_day/partial/batch/holiday',
    )
    processing_method = Column(
        String(20), nullable=True,
        comment='处置方式: auto_refund/reschedule/change_date/manual',
    )
    processing_status = Column(
        String(20), nullable=False, default='pending',
        comment='处置状态: pending/processing/completed/failed',
    )
    affected_appointment_count = Column(
        Integer, nullable=False, default=0,
        comment='受影响预约数',
    )
    reason = Column(String(500), nullable=True, comment='停诊原因')

    # 处置重试相关字段
    retry_count = Column(Integer, nullable=False, default=0, comment='处置重试次数')
    last_retry_at = Column(DateTime, nullable=True, comment='上次重试时间')

    # 关联关系
    tenant = relationship("Tenant", back_populates="schedule_suspensions")
    store = relationship("Store", backref="schedule_suspensions")
    doctor = relationship("Doctor", backref="schedule_suspensions")
