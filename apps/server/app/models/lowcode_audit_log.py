"""低代码页面审计日志模型。"""

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base, TimestampMixin
import uuid


class LowCodePageAuditLog(Base, TimestampMixin):
    """低代码页面操作审计日志。"""

    __tablename__ = "lowcode_page_audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    page_id = Column(
        String(36),
        ForeignKey("lowcode_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联页面ID",
    )
    operator_id = Column(
        String(36), nullable=False, comment="操作人ID"
    )
    action = Column(
        String(50), nullable=False, comment="操作类型: create/update/delete/publish/archive/rollback"
    )
    detail = Column(JSONB, nullable=True, comment="操作详情 (变更前后快照等)")

    __table_args__ = (
        {"comment": "低代码页面审计日志表"},
    )
