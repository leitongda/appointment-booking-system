from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, DateTime, String
from datetime import datetime

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
