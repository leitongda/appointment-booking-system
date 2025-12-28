from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base, AuditMixin
import uuid

class Department(Base, AuditMixin):
    __tablename__ = "departments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    parent_id = Column(String(36), ForeignKey("departments.id"))
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    is_hot = Column(Integer, default=0)  # 是否热门
    status = Column(Integer, default=1)  # 0禁用 1正常
    
    # 基础配置
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, comment="默认门店ID")
    tag = Column(String(100), nullable=True, comment="科室标签")
    enable_banner = Column(Integer, default=0, comment="是否开放banner 0禁用 1启用")
    enable_intro = Column(Integer, default=0, comment="是否开放科室简介 0禁用 1启用")
    is_final = Column(Integer, default=0, comment="是否终极科室 0否 1是")
    is_recommended = Column(Integer, default=0, comment="是否推荐 0否 1是")
    
    # 图片资源
    banner_image = Column(String(500), nullable=True, comment="banner图片URL")
    icon = Column(String(500), nullable=True, comment="科室图标URL")
    intro_images = Column(Text, nullable=True, comment="简介图片集JSON")
    
    # 详情内容
    intro_content = Column(Text, nullable=True, comment="富文本简介")
    features = Column(Text, nullable=True, comment="科室特色JSON数组")
    appointment_notice = Column(Text, nullable=True, comment="预约须知")
    
    # 联系信息
    phone = Column(String(20), nullable=True, comment="科室电话")
    location = Column(String(100), nullable=True, comment="位置/楼层")
    working_hours = Column(String(200), nullable=True, comment="工作时间")
    
    # 关联
    children = relationship("Department", backref="parent", remote_side=[id])
    doctors = relationship("Doctor", back_populates="department")
    store = relationship("Store", backref="departments")

