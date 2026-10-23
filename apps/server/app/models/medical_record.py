"""病历模型"""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class MedicalRecord(Base, AuditMixin):
    """病历表"""
    __tablename__ = "medical_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    record_no = Column(String(50), nullable=False, comment="病历号（租户内唯一）")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'record_no', name='uq_medical_records_tenant_no'),
        Index(
            'uq_medical_records_no_platform',
            'record_no',
            unique=True,
            postgresql_where=text('tenant_id IS NULL'),
            sqlite_where=text('tenant_id IS NULL'),
        ),
    )
    
    # 关联信息
    appointment_id = Column(String(36), ForeignKey("appointments.id"), nullable=False, comment="预约ID")
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, comment="患者ID")
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False, comment="医生ID")
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=False, comment="科室ID")
    
    # 病历内容
    chief_complaint = Column(Text, comment="主诉")
    present_illness = Column(Text, comment="现病史")
    past_history = Column(Text, comment="既往史")
    allergy_history = Column(Text, comment="过敏史")
    family_history = Column(Text, nullable=True, comment="家族史")
    medication_history = Column(Text, nullable=True, comment="用药史")
    physical_exam = Column(Text, comment="体格检查")
    auxiliary_exam = Column(Text, comment="辅助检查")
    diagnosis = Column(Text, nullable=False, comment="诊断")
    treatment = Column(Text, comment="治疗方案")
    prescription = Column(Text, comment="处方")
    advice = Column(Text, comment="医嘱")
    
    # 费用
    total_fee = Column(Numeric(10, 2), default=0, comment="总费用")
    
    # 状态 1草稿 2已完成
    status = Column(Integer, default=2, comment="状态")

    # 就诊时间
    visit_date = Column(DateTime, comment="就诊日期")

    # 软删除
    deleted_at = Column(DateTime, nullable=True, comment="软删除时间")
    
    # 关系
    appointment = relationship("Appointment", backref="medical_record")
    patient = relationship("Patient", backref="medical_records")
    doctor = relationship("Doctor", backref="medical_records")
    department = relationship("Department", backref="medical_records")

