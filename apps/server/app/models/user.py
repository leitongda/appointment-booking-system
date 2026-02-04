from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship as orm_relationship
from app.db.base import Base, AuditMixin
import uuid

class User(Base, AuditMixin):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = Column(String(20), unique=True, index=True, nullable=True)  # 微信用户可无手机号
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(50))
    avatar = Column(String(255))
    gender = Column(Integer, default=0)  # 0未知 1男 2女
    openid = Column(String(100), unique=True, index=True)
    status = Column(Integer, default=1)  # 0禁用 1正常
    points = Column(Integer, default=0)  # 当前积分
    
    # 微信相关字段
    unionid = Column(String(100), unique=True, index=True, nullable=True, comment="微信开放平台统一ID")
    wechat_nickname = Column(String(50), nullable=True, comment="微信原始昵称")
    wechat_avatar = Column(String(500), nullable=True, comment="微信原始头像URL")
    wechat_synced_at = Column(DateTime, nullable=True, comment="最后同步微信信息时间")
    
    patients = orm_relationship("Patient", back_populates="user")
    point_logs = orm_relationship("PointLog", back_populates="user")

class Patient(Base, AuditMixin):
    __tablename__ = "patients"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, index=True, comment="首次就诊门店ID")
    name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False)
    id_card = Column(String(18))
    gender = Column(Integer)
    age = Column(Integer, comment="年龄")  # 新增年龄字段
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
    store = orm_relationship("Store", backref="patients")

