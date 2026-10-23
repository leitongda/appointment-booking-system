import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base
from app.enums.message import MessageType  # noqa: F401 — re-export for backward compat


class Message(Base, AuditMixin):
    """消息模型"""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, index=True, comment="所属门店ID，NULL表示全局")
    user_id = Column(String(36), nullable=False, index=True, comment="接收用户ID")
    user_type = Column(String(20), nullable=False, comment="用户类型: patient/doctor")
    title = Column(String(200), nullable=False, comment="消息标题")
    content = Column(Text, comment="消息内容")
    message_type = Column(String(20), default=MessageType.SYSTEM.value, comment="消息类型")
    related_id = Column(String(36), comment="关联业务ID")
    is_read = Column(Integer, default=0, comment="是否已读: 0-未读 1-已读")
    read_at = Column(DateTime, comment="阅读时间")
    
    # 额外数据，JSON格式存储
    extra_data = Column(Text, comment="额外数据(JSON)")
    
    store = relationship("Store", backref="messages")


class MessageTemplate(Base, AuditMixin):
    """消息模板"""
    __tablename__ = "message_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    code = Column(String(50), nullable=False, comment="模板编码（租户内唯一，NULL 租户为平台模板）")

    __table_args__ = (
        UniqueConstraint('tenant_id', 'code', name='uq_message_templates_tenant_code'),
        Index(
            'uq_message_templates_code_platform',
            'code',
            unique=True,
            postgresql_where=text('tenant_id IS NULL'),
            sqlite_where=text('tenant_id IS NULL'),
        ),
    )
    name = Column(String(100), nullable=False, comment="模板名称")
    message_type = Column(String(20), nullable=False, comment="消息类型")
    title_template = Column(String(200), nullable=False, comment="标题模板")
    content_template = Column(Text, nullable=False, comment="内容模板")
    description = Column(String(255), comment="模板说明")
    status = Column(Integer, default=1, comment="状态: 0-禁用 1-启用")
