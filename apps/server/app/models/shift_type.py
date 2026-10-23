"""班次类型模型"""
import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


class ShiftType(Base, AuditMixin):
    """班次类型表"""
    __tablename__ = "shift_types"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), nullable=False, comment="类型代码（租户内唯一，NULL 租户为平台级）")
    name = Column(String(100), nullable=False, comment="类型名称")
    description = Column(Text, comment="描述")
    enabled = Column(Boolean, nullable=False, default=True, comment="是否启用")
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'code', name='uq_shift_types_tenant_code'),
        Index(
            'uq_shift_types_code_platform',
            'code',
            unique=True,
            postgresql_where=text('tenant_id IS NULL'),
            sqlite_where=text('tenant_id IS NULL'),
        ),
    )

    # 关联关系
    schedules = relationship("Schedule", backref="shift_type")
    rule_sets = relationship("RuleSet", secondary="rule_set_shift_types", back_populates="shift_types")
