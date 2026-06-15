"""预约须知模型"""
import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, Text

from app.db.base import AuditMixin, Base


class BookingNotice(Base, AuditMixin):
    """预约须知表"""
    __tablename__ = "booking_notices"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    type = Column(String(50), nullable=False, comment="类型: BOOKING/VISIT/REFUND")
    title = Column(String(100), nullable=True, comment="标题")
    content = Column(Text, nullable=True, comment="内容")
    sort_order = Column(Integer, default=0, comment="排序")
    status = Column(Integer, default=1, comment="状态: 0禁用 1启用")

