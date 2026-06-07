from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base, AuditMixin
from datetime import datetime
import uuid


class AppointmentSatisfaction(Base, AuditMixin):
    """预约满意度模型"""
    __tablename__ = "appointment_satisfactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    appointment_id = Column(String(36), ForeignKey("appointments.id"), nullable=False, comment="预约ID")
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True, comment="评价用户ID")
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=True, comment="就诊人ID")
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False, index=True, comment="医生ID")

    overall_score = Column(Integer, nullable=False, comment="综合评分 1-5")
    service_score = Column(Integer, nullable=True, comment="服务态度评分 1-5")
    environment_score = Column(Integer, nullable=True, comment="环境评分 1-5")
    comment = Column(Text, comment="评价内容")
    tags = Column(JSON, nullable=True, comment="评价标签(JSON数组)")

    submitted_at = Column(DateTime, default=datetime.utcnow, comment="提交时间")

    # 关联关系
    appointment = relationship("Appointment", backref="satisfaction")
    user = relationship("User", backref="satisfaction_surveys")

    # 一个预约只能提交一次满意度
    __table_args__ = (
        UniqueConstraint('appointment_id', name='uq_satisfaction_appointment'),
        {'comment': '预约满意度表'},
    )
