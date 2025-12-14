from sqlalchemy import Column, String, Integer, Time, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin
import uuid


class ScheduleTemplate(Base, TimestampMixin):
    """排班模板模型"""
    __tablename__ = "schedule_templates"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, comment="模板名称")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False, comment="门店ID")
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False, comment="医生ID")
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=False, comment="科室ID")
    weekday = Column(Integer, nullable=False, comment="星期 1-7")
    appointment_type = Column(String(20), default="normal", comment="预约类型: urgent/normal/expert/medical_insurance/self_pay")
    start_time = Column(Time, nullable=False, comment="开始时间")
    end_time = Column(Time, nullable=False, comment="结束时间")
    total_slots = Column(Integer, default=10, comment="班次人数")
    schedule_mode = Column(String(50), default="weekly", comment="排班方式")
    status = Column(Integer, default=1, comment="状态: 0禁用 1启用")
    
    # 关联关系
    store = relationship("Store", backref="schedule_templates")
    doctor = relationship("Doctor", backref="schedule_templates")
    department = relationship("Department", backref="schedule_templates")
    schedules = relationship("Schedule", back_populates="template")
