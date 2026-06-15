import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class DoctorReview(Base, AuditMixin):
    """医生评价模型"""
    __tablename__ = "doctor_reviews"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    appointment_id = Column(String(36), ForeignKey("appointments.id"), nullable=False, comment="预约ID")
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False, index=True, comment="医生ID")
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True, comment="评价用户ID")
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=True, comment="就诊人ID")

    rating = Column(Integer, nullable=False, comment="评分 1-5")
    content = Column(Text, comment="评价内容")
    tags = Column(JSON, nullable=True, comment="评价标签(JSON数组)")
    is_anonymous = Column(Boolean, default=False, comment="是否匿名")

    status = Column(Integer, default=1, comment="状态: 0-隐藏 1-正常 2-置顶")
    reply = Column(Text, comment="医生/管理回复")
    reply_at = Column(DateTime, comment="回复时间")

    # 关联关系
    appointment = relationship("Appointment", backref="reviews")
    doctor = relationship("Doctor", backref="reviews")
    user = relationship("User", backref="doctor_reviews")

    # 一个预约只能评价一次
    __table_args__ = (
        UniqueConstraint('appointment_id', name='uq_doctor_reviews_appointment'),
        {'comment': '医生评价表'},
    )
