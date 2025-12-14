from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship as orm_relationship
from app.db.base import Base, TimestampMixin
import uuid

class User(Base, TimestampMixin):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = Column(String(20), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(50))
    avatar = Column(String(255))
    gender = Column(Integer, default=0)  # 0未知 1男 2女
    openid = Column(String(100), unique=True, index=True)
    status = Column(Integer, default=1)  # 0禁用 1正常
    points = Column(Integer, default=0)  # 当前积分
    
    patients = orm_relationship("Patient", back_populates="user")
    point_logs = orm_relationship("PointLog", back_populates="user")

class Patient(Base, TimestampMixin):
    __tablename__ = "patients"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False)
    id_card = Column(String(18))
    gender = Column(Integer)
    birthday = Column(DateTime)
    relationship = Column(String(20))  # 与账号用户关系
    is_default = Column(Boolean, default=False)
    
    # 新增字段
    card_no = Column(String(50), unique=True, index=True)  # 就诊卡编号
    province = Column(String(50))  # 省
    city = Column(String(50))  # 市
    district = Column(String(50))  # 区
    street = Column(String(100))  # 街道/社区
    id_card_type = Column(Integer, default=1)  # 证件类型: 1身份证 2户口簿 3护照
    ethnicity = Column(String(20), default="汉族")  # 民族
    address = Column(String(255))  # 详细地址
    source = Column(Integer, default=1)  # 来源: 1用户添加 2管理员添加
    total_consumption = Column(Numeric(10, 2), default=0)  # 累计消费
    
    user = orm_relationship("User", back_populates="patients")

