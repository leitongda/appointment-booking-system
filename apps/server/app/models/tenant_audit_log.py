"""租户操作审计日志模型

记录租户级别的关键操作审计信息，包括：
- 配额变更
- 状态变更
- 订阅变更
- 计划变更
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text

from app.db.base import Base


class TenantAuditLog(Base):
    __tablename__ = "tenant_audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
        comment="租户ID",
    )

    # 事件类型: status_change / quota_change / subscription_change / plan_change
    event_type = Column(String(50), nullable=False, comment="事件类型")

    # 操作人信息
    actor_id = Column(String(36), nullable=True, comment="操作人ID")
    actor_type = Column(
        String(20), nullable=True, comment="操作人类型: admin/platform_admin/system"
    )
    actor_name = Column(String(50), nullable=True, comment="操作人名称")

    # 操作资源
    resource_type = Column(String(50), nullable=False, comment="资源类型")
    resource_id = Column(String(36), nullable=False, comment="资源ID")
    action = Column(String(50), nullable=False, comment="具体操作")

    # 变更前后数据快照（JSON 格式）
    before_data = Column(Text, nullable=True, comment="变更前数据快照(JSON)")
    after_data = Column(Text, nullable=True, comment="变更后数据快照(JSON)")

    # 请求来源信息
    ip_address = Column(String(50), nullable=True, comment="IP地址")
    user_agent = Column(String(255), nullable=True, comment="User-Agent")

    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    __table_args__ = (
        Index("ix_tenant_audit_logs_tenant_created", "tenant_id", "created_at"),
        Index(
            "ix_tenant_audit_logs_tenant_event", "tenant_id", "event_type"
        ),
        {"comment": "租户操作审计日志表"},
    )
