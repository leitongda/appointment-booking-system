from sqlalchemy import Column, String, Integer, Date, Time, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base, AuditMixin
import uuid


class CustomSchedule(Base, AuditMixin):
    """自定义排班（单日排班）模型"""
    __tablename__ = "custom_schedules"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False, comment="门店ID")
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=False, comment="科室ID")
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False, comment="医生ID")
    schedule_date = Column(Date, nullable=False, comment="排班日期")
    start_time = Column(Time, nullable=False, comment="开始时间")
    end_time = Column(Time, nullable=False, comment="结束时间")
    appointment_type = Column(String(20), nullable=False, comment="预约类型: urgent/normal/expert/medical_insurance/self_pay")
    max_patients = Column(Integer, default=1, comment="预约人数（每个班次）")
    booked_count = Column(Integer, default=0, comment="已预约数")
    status = Column(Integer, default=1, comment="状态: 0停用 1启用")
    
    # 关联关系
    store = relationship("Store", backref="custom_schedules")
    department = relationship("Department", backref="custom_schedules")
    doctor = relationship("Doctor", backref="custom_schedules")
