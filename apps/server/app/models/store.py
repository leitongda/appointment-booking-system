from sqlalchemy import Column, String, Integer, Text, Time
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin
import uuid


class Store(Base, TimestampMixin):
    """门店/分院模型"""
    __tablename__ = "stores"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, comment="门店名称")
    code = Column(String(50), unique=True, comment="门店编码")
    address = Column(String(255), comment="详细地址")
    province = Column(String(50), comment="省份")
    city = Column(String(50), comment="城市")
    district = Column(String(50), comment="区县")
    latitude = Column(String(20), comment="纬度")
    longitude = Column(String(20), comment="经度")
    phone = Column(String(50), comment="联系电话")
    contact_person = Column(String(50), comment="联系人")
    description = Column(Text, comment="门店简介")
    opening_time = Column(Time, comment="营业开始时间")
    closing_time = Column(Time, comment="营业结束时间")
    working_days = Column(String(50), default="1,2,3,4,5,6,7", comment="工作日(1-7)")
    image = Column(String(255), comment="门店图片")
    sort_order = Column(Integer, default=0, comment="排序")
    status = Column(Integer, default=1, comment="状态: 0-停业 1-营业")
    
    # 关联关系
    departments = relationship("StoreDepartment", back_populates="store", cascade="all, delete-orphan")


class StoreDepartment(Base, TimestampMixin):
    """门店-科室关联表"""
    __tablename__ = "store_departments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id = Column(String(36), nullable=False, comment="门店ID")
    department_id = Column(String(36), nullable=False, comment="科室ID")
    floor = Column(String(20), comment="楼层")
    room = Column(String(50), comment="诊室")
    status = Column(Integer, default=1, comment="状态: 0-停诊 1-正常")
    
    store = relationship("Store", back_populates="departments")
