from sqlalchemy import Column, String, Integer, Date, Time, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin
import uuid

class Schedule(Base, TimestampMixin):
    __tablename__ = "schedules"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False)
    schedule_date = Column(Date, nullable=False)
    time_slot = Column(String(10), nullable=False)  # AM/PM
    start_time = Column(Time)
    end_time = Column(Time)
    total_slots = Column(Integer, default=10)  # 总号源
    booked_slots = Column(Integer, default=0)  # 已预约数
    status = Column(Integer, default=1)  # 0停诊 1正常
    
    doctor = relationship("Doctor", back_populates="schedules")
    appointments = relationship("Appointment", back_populates="schedule")

