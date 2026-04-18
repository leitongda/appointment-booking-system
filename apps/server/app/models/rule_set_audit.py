"""规则组审计日志模型"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text

from app.db.base import Base


class RuleSetAuditLog(Base):
    __tablename__ = "rule_set_audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_set_id = Column(String(36), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    action = Column(String(30), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(36), nullable=False)
    operator_id = Column(String(36), nullable=True)
    snapshot_before = Column(Text, nullable=True)
    snapshot_after = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
