"""排班审计日志模型"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text

from app.db.base import Base


class ScheduleAuditLog(Base):
    __tablename__ = "schedule_audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    schedule_id = Column(String(36), nullable=True, index=True, comment="排班ID（批量操作可为空）")
    tenant_id = Column(String(36), nullable=False, index=True)
    action = Column(String(50), nullable=False, comment="操作类型: publish/suspend/resume/delete/withdraw/drag/copy")
    operator_id = Column(String(36), nullable=True)
    snapshot_before = Column(Text, nullable=True, comment="操作前排班快照 JSON")
    snapshot_after = Column(Text, nullable=True, comment="操作后排班快照 JSON")
    changes = Column(Text, nullable=True, comment="字段级变更差异 JSON")
    created_at = Column(DateTime, default=datetime.utcnow)
