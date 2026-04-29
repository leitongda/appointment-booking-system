import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON

from app.db.base import Base


class SupportTicketType(str, enum.Enum):
    """工单类型"""

    SUGGESTION = "suggestion"  # 建议
    COMPLAINT = "complaint"  # 投诉
    BUG = "bug"  # 缺陷
    OTHER = "other"  # 其他


class SupportTicketStatus(str, enum.Enum):
    """工单状态"""

    PENDING = "pending"  # 待处理
    PROCESSING = "processing"  # 处理中
    RESOLVED = "resolved"  # 已解决
    CLOSED = "closed"  # 已关闭


class SupportTicketPriority(str, enum.Enum):
    """工单优先级"""

    LOW = "low"  # 低
    MEDIUM = "medium"  # 中
    HIGH = "high"  # 高
    URGENT = "urgent"  # 紧急


class SupportTicket(Base):
    """工单支持模型"""

    __tablename__ = "support_tickets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=True,
        index=True,
        comment="租户ID",
    )
    title = Column(String(200), nullable=False, comment="工单标题")
    description = Column(Text, nullable=False, comment="工单描述")
    type = Column(
        String(20),
        default=SupportTicketType.OTHER.value,
        comment="工单类型: suggestion/complaint/bug/other",
    )
    status = Column(
        String(20),
        default=SupportTicketStatus.PENDING.value,
        comment="状态: pending/processing/resolved/closed",
    )
    priority = Column(
        String(20),
        default=SupportTicketPriority.MEDIUM.value,
        comment="优先级: low/medium/high/urgent",
    )
    creator_id = Column(String(36), nullable=False, index=True, comment="创建人ID")
    creator_type = Column(
        String(20),
        nullable=False,
        default="user",
        comment="创建人类型: user/admin",
    )
    assignee_id = Column(String(36), nullable=True, comment="处理人ID")
    contact_info = Column(String(200), nullable=True, comment="联系方式")
    attachments = Column(JSON, nullable=True, comment="附件列表(JSON)")
    resolution = Column(Text, nullable=True, comment="解决方案/备注")
    closed_at = Column(DateTime, nullable=True, comment="关闭时间")
    created_at = Column(
        DateTime, default=datetime.utcnow, nullable=False, comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="更新时间",
    )

    __table_args__ = (
        Index(
            "ix_support_tickets_tenant_status",
            "tenant_id",
            "status",
        ),
        Index(
            "ix_support_tickets_tenant_created",
            "tenant_id",
            "created_at",
        ),
    )
