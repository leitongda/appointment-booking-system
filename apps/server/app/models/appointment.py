from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin
from datetime import datetime
import uuid

class Appointment(Base, TimestampMixin):
    __tablename__ = "appointments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    appointment_no = Column(String(50), unique=True, nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False)
    schedule_id = Column(String(36), ForeignKey("schedules.id"), nullable=False)
    queue_number = Column(Integer)  # 队列号
    status = Column(Integer, default=1)  # 1待确认 2已签到 3就诊中 4已过号 5已完成 6已取消 7已爽约
    sign_in_time = Column(DateTime)
    call_time = Column(DateTime)
    complete_time = Column(DateTime)
    cancel_time = Column(DateTime)
    cancel_reason = Column(Text)
    remark = Column(Text)
    
    schedule = relationship("Schedule", back_populates="appointments")

