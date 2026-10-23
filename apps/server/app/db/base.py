from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

class TimestampMixin:
    """时间戳混入类，提供创建时间和更新时间"""
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")


class AuditMixin(TimestampMixin):
    """审计混入类，提供完整的审计信息（时间戳+操作人）"""
    created_by = Column(String(36), nullable=True, comment="创建人ID")
    updated_by = Column(String(36), nullable=True, comment="更新人ID")


class TenantMixin:
    """租户混入类：为共享库多租户表提供统一的 tenant_id 列。

    NULL 表示平台级/全局数据。
    """
    tenant_id = Column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=True,
        index=True,
        comment="租户ID（NULL表示平台级/全局）",
    )
