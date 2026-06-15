"""Examination Report model — 检查报告"""
import uuid

from sqlalchemy import BigInteger, Column, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class ExaminationReport(Base, AuditMixin):
    """检查报告表"""
    __tablename__ = "examination_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)
    store_id = Column(String(36), nullable=True, index=True)

    # 关联信息
    record_id = Column(String(36), ForeignKey("medical_records.id"), nullable=True, index=True, comment="关联病历ID")
    appointment_id = Column(String(36), ForeignKey("appointments.id"), nullable=False, index=True, comment="关联预约ID")
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True, comment="患者ID")
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False, index=True, comment="医生ID")

    # 报告信息
    report_type = Column(String(50), nullable=False, comment="报告类型: blood_test/imaging/pathology/other")
    title = Column(String(200), nullable=False, comment="报告标题")
    description = Column(Text, nullable=True, comment="报告描述/备注")

    # 文件信息
    file_name = Column(String(255), nullable=False, comment="原始文件名")
    file_key = Column(String(500), nullable=False, comment="存储key")
    file_size = Column(BigInteger, nullable=False, comment="文件大小(bytes)")
    file_type = Column(String(50), nullable=False, comment="MIME类型")
    file_url = Column(String(1000), nullable=True, comment="文件访问URL")

    # 关系
    record = relationship("MedicalRecord", backref="examination_reports", lazy="selectin")
    appointment = relationship("Appointment", backref="examination_reports", lazy="selectin")
    patient = relationship("Patient", backref="examination_reports", lazy="selectin")
    doctor = relationship("Doctor", backref="examination_reports", lazy="selectin")
