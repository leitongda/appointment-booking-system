import uuid

from sqlalchemy import Column, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class RestDay(Base, AuditMixin):
    """休息日设置模型"""
    __tablename__ = "rest_days"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False, comment="门店ID")
    doctor_ids = Column(Text, nullable=True, comment="医生ID列表,JSON数组,NULL表示门店所有医生")
    reason = Column(String(255), comment="休息原因")
    start_date = Column(Date, nullable=False, comment="开始日期")
    end_date = Column(Date, nullable=False, comment="结束日期")
    status = Column(Integer, default=1, comment="状态: 0已取消 1生效中")
    
    # 关联关系
    store = relationship("Store", backref="rest_days")
