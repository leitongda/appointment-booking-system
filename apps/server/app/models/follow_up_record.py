"""随访记录模型"""
import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class FollowUpRecord(Base, AuditMixin):
    """随访记录表"""
    __tablename__ = "follow_up_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")

    # 关联信息
    task_id = Column(String(36), ForeignKey("follow_up_tasks.id"), nullable=True, index=True, comment="任务ID，NULL=独立记录")
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True, comment="患者ID")
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False, index=True, comment="医生ID")
    appointment_id = Column(String(36), ForeignKey("appointments.id"), nullable=True, index=True, comment="预约ID")
    medical_record_id = Column(String(36), ForeignKey("medical_records.id"), nullable=True, index=True, comment="病历ID")

    # 随访信息
    follow_up_date = Column(DateTime, nullable=False, comment="实际随访时间")
    content = Column(Text, nullable=False, comment="随访内容")
    patient_condition = Column(String(20), nullable=True, comment="患者状况: improved/stable/worsened")
    next_action = Column(Text, nullable=True, comment="下一步措施")
    next_follow_up_date = Column(Date, nullable=True, comment="下次随访日期")
    attachments = Column(Text, nullable=True, comment="附件JSON数组")

    # 软删除
    deleted_at = Column(DateTime, nullable=True, comment="软删除时间")

    # 关系
    patient = relationship("Patient", backref="follow_up_records")
    doctor = relationship("Doctor", backref="follow_up_records")
    appointment = relationship("Appointment", backref="follow_up_records")
    medical_record = relationship("MedicalRecord", backref="follow_up_records")
