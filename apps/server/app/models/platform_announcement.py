"""平台公告模型

支持向全部租户或指定租户列表广播消息。
发布后，系统会为每个目标租户生成一条 TenantNotification 记录。
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String, Text

from app.db.base import Base


class PlatformAnnouncement(Base):
    __tablename__ = "platform_announcements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False, comment="公告标题")
    content = Column(Text, nullable=False, comment="公告内容")

    # 目标范围: all / specific
    target_type = Column(String(20), nullable=False, default="all", comment="目标类型: all-全部租户 specific-指定租户")
    # 指定租户ID列表（JSON数组），target_type=specific 时生效
    target_tenant_ids = Column(Text, nullable=True, comment="目标租户ID列表(JSON)")

    # 状态: draft / published / revoked
    status = Column(String(20), nullable=False, default="draft", comment="状态: draft-草稿 published-已发布 revoked-已撤回")

    # 优先级: 0-普通 1-重要 2-紧急
    priority = Column(Integer, default=0, comment="优先级")

    # 发布控制
    publish_at = Column(DateTime, nullable=True, comment="定时发布时间")
    expire_at = Column(DateTime, nullable=True, comment="过期时间")

    # 发布人
    publisher_id = Column(String(36), nullable=True, comment="发布人ID")
    publisher_name = Column(String(50), nullable=True, comment="发布人名称")

    # 阅读统计（冗余字段，减少查询压力）
    read_count = Column(Integer, default=0, comment="已读数量")
    total_count = Column(Integer, default=0, comment="目标租户总数")

    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    __table_args__ = (
        Index("ix_platform_announcements_status", "status"),
        Index("ix_platform_announcements_publish_at", "publish_at"),
        {"comment": "平台公告表"},
    )
