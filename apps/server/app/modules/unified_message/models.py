"""统一消息中心数据模型

6 张新表：notification_groups, notification_recipients, notification_deliveries,
unified_templates, channel_strategies, recipient_rules
"""
import uuid

# is_read 状态常量（NotificationRecipient.is_read 字段）
READ_STATUS_UNREAD = 0    # 未读
READ_STATUS_READ = 1      # 已读
READ_STATUS_DELETED = 2   # 已删除（软删除）
READ_STATUS_ARCHIVED = 3  # 已归档

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


def _uuid() -> str:
    return str(uuid.uuid4())


class NotificationGroup(Base, TimestampMixin):
    """通知组：一次业务事件生成一个通知组，关联多个渠道的发送记录"""
    __tablename__ = "notification_groups"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    store_id = Column(String(36), nullable=True, index=True, comment="门店ID")
    event_type = Column(String(50), nullable=False, comment="事件类型: appointment.success / appointment.reminder.24h")
    template_code = Column(String(50), nullable=True, comment="关联 UnifiedTemplate.code")
    message_type = Column(String(30), nullable=False, comment="消息类型: appointment / system / stop_clinic / schedule")
    priority = Column(String(10), default="medium", comment="优先级: critical / high / medium / low")
    variables = Column(JSON, nullable=True, comment="模板变量")
    related_id = Column(String(36), nullable=True, comment="关联业务ID")
    dedup_key = Column(String(200), unique=True, nullable=True, comment="去重键")
    status = Column(String(20), default="pending", comment="状态: pending / partial / sent / failed")
    legacy_message_id = Column(String(36), nullable=True, comment="旧表 messages.id（数据迁移回溯用）")

    recipients = relationship("NotificationRecipient", back_populates="group", lazy="selectin")
    deliveries = relationship("NotificationDelivery", back_populates="group", lazy="selectin")


class NotificationRecipient(Base, TimestampMixin):
    """接收人记录：通知组下的每个接收人"""
    __tablename__ = "notification_recipients"

    id = Column(String(36), primary_key=True, default=_uuid)
    group_id = Column(String(36), ForeignKey("notification_groups.id"), nullable=False, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    user_id = Column(String(36), nullable=False, index=True, comment="接收用户ID")
    user_type = Column(String(20), nullable=False, comment="用户类型: patient/doctor/admin")
    # 站内信数据（复用 Message 语义）
    title = Column(String(200), nullable=True, comment="消息标题")
    content = Column(Text, nullable=True, comment="消息内容")
    is_read = Column(Integer, default=0, comment="状态: 0-未读 1-已读 2-已删除(软删除)")
    read_at = Column(DateTime, nullable=True, comment="阅读时间")
    # 联系方式（真实地址，重试发送依赖真实地址）
    phone = Column(String(20), nullable=True, comment="手机号")
    email = Column(String(100), nullable=True, comment="邮箱")
    openid = Column(String(100), nullable=True, comment="微信 OpenID")
    status = Column(String(20), default="pending", comment="状态: pending / sent / failed")

    group = relationship("NotificationGroup", back_populates="recipients")
    deliveries = relationship("NotificationDelivery", back_populates="recipient", lazy="selectin")


class NotificationDelivery(Base, TimestampMixin):
    """投递记录：每个接收人 x 每个渠道 = 一条记录（替代 NotificationLog）"""
    __tablename__ = "notification_deliveries"

    id = Column(String(36), primary_key=True, default=_uuid)
    group_id = Column(String(36), ForeignKey("notification_groups.id"), nullable=False, index=True)
    recipient_id = Column(String(36), ForeignKey("notification_recipients.id"), nullable=False, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    channel = Column(String(20), nullable=False, index=True, comment="渠道: in_app / sms / email / wechat / websocket")
    status = Column(String(20), nullable=False, default="pending", index=True, comment="状态: pending / sent / failed / permanently_failed")
    recipient_address = Column(String(200), nullable=True, comment="接收地址（手机号/邮箱/openid）")
    error_message = Column(Text, nullable=True, comment="错误信息")
    retry_count = Column(Integer, default=0, comment="已重试次数")
    max_retries = Column(Integer, default=3, comment="最大重试次数")
    next_retry_at = Column(DateTime, nullable=True, comment="下次重试时间")
    sent_at = Column(DateTime, nullable=True, comment="实际发送时间")
    extra_data = Column(JSON, nullable=True, comment="额外数据")
    legacy_log_id = Column(String(36), nullable=True, comment="旧表 notification_logs.id（数据迁移回溯用）")

    group = relationship("NotificationGroup", back_populates="deliveries")
    recipient = relationship("NotificationRecipient", back_populates="deliveries")


# UnifiedTemplate 已迁移至 app.models.unified_template（消除 infrastructure -> modules 反向依赖）
# 此处保留 re-export 供 unified_message 模块内部使用
from app.models.unified_template import UnifiedTemplate  # noqa: E402, F401


class ChannelStrategy(Base, TimestampMixin):
    """渠道策略：按事件类型配置"""
    __tablename__ = "channel_strategies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "event_type", name="uq_channel_strategy_tenant_event"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    event_type = Column(String(50), nullable=False, comment="事件类型")
    channels = Column(JSON, nullable=False, comment='渠道列表: ["email", "sms", "in_app"]')
    strategy = Column(String(20), default="fallback", comment="策略: fallback / parallel / all")
    dedup_window_seconds = Column(Integer, default=0, comment="去重窗口(秒): 0=不去重, 86400=24h")
    priority = Column(String(10), default="medium", comment="优先级: critical / high / medium / low")
    quiet_hours_exempt = Column(Boolean, default=False, comment="是否豁免静默时段")
    status = Column(Integer, default=1, comment="状态: 0-禁用 1-启用")


class RecipientRule(Base, TimestampMixin):
    """接收人规则"""
    __tablename__ = "recipient_rules"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    name = Column(String(100), nullable=False, comment="规则名称")
    rule_type = Column(String(30), nullable=False, comment="规则类型: role / department / user_list / dynamic / event_driven")
    rule_config = Column(JSON, nullable=False, comment="规则配置")
    event_type = Column(String(50), nullable=True, comment="绑定的事件类型（可选）")
    status = Column(Integer, default=1, comment="状态: 0-禁用 1-启用")
