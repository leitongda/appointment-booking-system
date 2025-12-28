from sqlalchemy import Column, String, Integer, Text, Numeric, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base, AuditMixin
import uuid


class ConsultationFeeType(Base, AuditMixin):
    """诊费类型模型"""
    __tablename__ = "consultation_fee_types"
    __table_args__ = (
        UniqueConstraint('store_id', 'code', name='uq_consultation_fee_types_store_code'),
    )
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id = Column(String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=True, 
                      comment="门店ID，NULL表示全局类型")
    name = Column(String(50), nullable=False, comment="诊费类型名称")
    code = Column(String(50), index=True, comment="类型编码")
    description = Column(String(255), comment="描述")
    sort_order = Column(Integer, default=0, comment="排序")
    status = Column(Integer, default=1, comment="状态: 0禁用 1启用")
    
    # 关联关系
    store = relationship("Store", backref="consultation_fee_types")
    templates = relationship("ConsultationFeeTemplate", back_populates="fee_type")
    store_templates = relationship("StoreFeeTemplate", back_populates="fee_type")
    doctor_fees = relationship("DoctorConsultationFee", back_populates="fee_type")


class ConsultationFeeTemplate(Base, AuditMixin):
    """诊费模板模型（全局默认诊费配置）"""
    __tablename__ = "consultation_fee_templates"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    fee_type_id = Column(String(36), ForeignKey("consultation_fee_types.id"), nullable=False, unique=True, comment="诊费类型ID")
    initial_fee = Column(Numeric(10, 2), default=0, comment="初诊金额")
    follow_up_fee = Column(Numeric(10, 2), default=0, comment="复诊金额")
    status = Column(Integer, default=1, comment="状态: 0禁用 1启用")
    
    # 关联关系
    fee_type = relationship("ConsultationFeeType", back_populates="templates")


class StoreFeeTemplate(Base, AuditMixin):
    """门店诊费模板模型（门店级别的诊费配置，可覆盖全局模板）"""
    __tablename__ = "store_fee_templates"
    __table_args__ = (
        UniqueConstraint('store_id', 'fee_type_id', name='uq_store_fee_templates_store_type'),
    )
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id = Column(String(36), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, comment="门店ID")
    fee_type_id = Column(String(36), ForeignKey("consultation_fee_types.id", ondelete="CASCADE"), nullable=False, comment="诊费类型ID")
    initial_fee = Column(Numeric(10, 2), default=0, comment="初诊金额")
    follow_up_fee = Column(Numeric(10, 2), default=0, comment="复诊金额")
    status = Column(Integer, default=1, comment="状态: 0禁用 1启用")
    
    # 关联关系
    store = relationship("Store", backref="fee_templates")
    fee_type = relationship("ConsultationFeeType", back_populates="store_templates")


class DoctorConsultationFee(Base, AuditMixin):
    """医生诊费配置模型"""
    __tablename__ = "doctor_consultation_fees"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False, comment="医生ID")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False, comment="门店ID")
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=False, comment="科室ID")
    fee_type_id = Column(String(36), ForeignKey("consultation_fee_types.id"), nullable=False, comment="诊费类型ID")
    initial_fee = Column(Numeric(10, 2), default=0, comment="初诊金额")
    follow_up_fee = Column(Numeric(10, 2), default=0, comment="复诊金额")
    status = Column(Integer, default=1, comment="状态: 0禁用 1启用")
    
    # 关联关系
    doctor = relationship("Doctor", back_populates="consultation_fees")
    store = relationship("Store")
    department = relationship("Department")
    fee_type = relationship("ConsultationFeeType", back_populates="doctor_fees")
