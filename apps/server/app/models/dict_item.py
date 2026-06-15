"""字典项模型"""
import uuid

from sqlalchemy import JSON, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class DictItem(Base, AuditMixin):
    """字典项表"""
    __tablename__ = "dict_items"
    __table_args__ = (
        UniqueConstraint("dict_type_id", "value", "tenant_id", name="uq_dict_item_value_tenant"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dict_type_id = Column(String(36), ForeignKey("dict_types.id", ondelete="CASCADE"), nullable=False, index=True, comment="字典类型ID")
    label = Column(String(200), nullable=False, comment="显示标签")
    value = Column(String(100), nullable=False, comment="字典值")
    sort_order = Column(Integer, nullable=False, default=0, comment="排序")
    status = Column(Integer, nullable=False, default=1, comment="状态 1=启用 0=禁用")
    extra = Column(JSON, nullable=True, comment="扩展数据（颜色、图标等）")
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")

    # 关联关系
    dict_type = relationship("DictType", backref="items")
