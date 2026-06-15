"""字典类型模型"""
import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint

from app.db.base import AuditMixin, Base


class DictType(Base, AuditMixin):
    """字典类型表"""
    __tablename__ = "dict_types"
    __table_args__ = (
        UniqueConstraint("code", "tenant_id", name="uq_dict_type_code_tenant"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), nullable=False, comment="字典类型编码")
    name = Column(String(100), nullable=False, comment="字典类型名称")
    description = Column(Text, nullable=True, comment="描述")
    status = Column(Integer, nullable=False, default=1, comment="状态 1=启用 0=禁用")
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
