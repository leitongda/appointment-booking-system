"""数据权限范围模型"""
from sqlalchemy import Column, String, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base, AuditMixin
import uuid


class DataScope(Base, AuditMixin):
    """数据权限范围表

    定义角色可访问的数据范围：
    - all: 不限制，可查看所有数据
    - tenant: 按租户过滤
    - store: 按门店过滤（当前门店或指定门店列表）
    - custom: 按自定义门店列表过滤
    """
    __tablename__ = "data_scopes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID（NULL表示平台级）")
    name = Column(String(100), nullable=False, comment="范围名称")
    scope_type = Column(String(20), nullable=False, comment="范围类型: all/tenant/store/custom")
    store_ids = Column(Text, nullable=True, comment="门店ID列表，JSON格式，scope_type=custom 时使用")
    description = Column(String(200), nullable=True, comment="描述")

    # 关联关系
    roles = relationship("Role", back_populates="data_scope")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'name', name='uq_data_scope_tenant_name'),
        {'comment': '数据权限范围表'},
    )
