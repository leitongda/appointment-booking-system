from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin
import uuid

class Department(Base, TimestampMixin):
    __tablename__ = "departments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    parent_id = Column(String(36), ForeignKey("departments.id"))
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    is_hot = Column(Integer, default=0)  # 是否热门
    status = Column(Integer, default=1)  # 0禁用 1正常
    
    children = relationship("Department", backref="parent", remote_side=[id])
    doctors = relationship("Doctor", back_populates="department")

