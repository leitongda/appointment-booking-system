from sqlalchemy import Column, String, Integer, Text, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin
import uuid

class Doctor(Base, TimestampMixin):
    __tablename__ = "doctors"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"))
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=False)
    name = Column(String(50), nullable=False)
    phone = Column(String(20), unique=True, index=True)
    password_hash = Column(String(255))  # 登录密码
    avatar = Column(String(255))
    title = Column(String(50))  # 职称
    specialty = Column(Text)  # 擅长
    introduction = Column(Text)  # 简介
    registration_fee = Column(Numeric(10, 2), default=0)  # 挂号费
    is_recommended = Column(Integer, default=0)  # 是否推荐
    sort_order = Column(Integer, default=0)
    status = Column(Integer, default=1)  # 0禁用 1正常
    last_login_at = Column(DateTime, comment="最后登录时间")
    last_login_ip = Column(String(50), comment="最后登录IP")
    
    department = relationship("Department", back_populates="doctors")
    schedules = relationship("Schedule", back_populates="doctor")

