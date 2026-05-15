"""Create unified message center tables

Revision ID: 084_create_unified_message_tables
Revises: 083_backfill_shift_type_id_for_templates
Create Date: 2026-05-14

6 new tables for the unified message center:
- notification_groups: one group per business event
- notification_recipients: one recipient per user
- notification_deliveries: one delivery per recipient x channel
- unified_templates: shared templates across channels
- channel_strategies: per-event channel configuration
- recipient_rules: recipient resolution rules
"""
from alembic import op
import sqlalchemy as sa


revision = "084_create_unified_message_tables"
down_revision = "083_backfill_shift_type_id_for_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- notification_groups ---
    op.create_table(
        "notification_groups",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, comment="租户ID"),
        sa.Column("store_id", sa.String(36), nullable=True, comment="门店ID"),
        sa.Column("event_type", sa.String(50), nullable=False, comment="事件类型"),
        sa.Column("template_code", sa.String(50), nullable=True, comment="关联模板编码"),
        sa.Column("message_type", sa.String(30), nullable=False, comment="消息类型"),
        sa.Column("priority", sa.String(10), server_default="medium", comment="优先级"),
        sa.Column("variables", sa.JSON, nullable=True, comment="模板变量"),
        sa.Column("related_id", sa.String(36), nullable=True, comment="关联业务ID"),
        sa.Column("dedup_key", sa.String(200), unique=True, nullable=True, comment="去重键"),
        sa.Column("status", sa.String(20), server_default="pending", comment="状态"),
        sa.Column("legacy_message_id", sa.String(36), nullable=True, comment="旧表 messages.id"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_notification_groups_tenant_id", "notification_groups", ["tenant_id"])
    op.create_index("ix_notification_groups_store_id", "notification_groups", ["store_id"])

    # --- notification_recipients ---
    op.create_table(
        "notification_recipients",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("group_id", sa.String(36), sa.ForeignKey("notification_groups.id"), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=False, comment="租户ID"),
        sa.Column("user_id", sa.String(36), nullable=False, comment="接收用户ID"),
        sa.Column("user_type", sa.String(20), nullable=False, comment="用户类型"),
        sa.Column("title", sa.String(200), nullable=True, comment="消息标题"),
        sa.Column("content", sa.Text, nullable=True, comment="消息内容"),
        sa.Column("is_read", sa.Integer, server_default="0", comment="是否已读"),
        sa.Column("read_at", sa.DateTime, nullable=True, comment="阅读时间"),
        sa.Column("phone", sa.String(20), nullable=True, comment="手机号"),
        sa.Column("email", sa.String(100), nullable=True, comment="邮箱"),
        sa.Column("openid", sa.String(100), nullable=True, comment="微信 OpenID"),
        sa.Column("status", sa.String(20), server_default="pending", comment="状态"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_notification_recipients_group_id", "notification_recipients", ["group_id"])
    op.create_index("ix_notification_recipients_tenant_id", "notification_recipients", ["tenant_id"])
    op.create_index("ix_notification_recipients_user_id", "notification_recipients", ["user_id"])

    # --- notification_deliveries ---
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("group_id", sa.String(36), sa.ForeignKey("notification_groups.id"), nullable=False),
        sa.Column("recipient_id", sa.String(36), sa.ForeignKey("notification_recipients.id"), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=False, comment="租户ID"),
        sa.Column("channel", sa.String(20), nullable=False, comment="渠道"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending", comment="状态"),
        sa.Column("recipient_address", sa.String(200), nullable=True, comment="接收地址"),
        sa.Column("error_message", sa.Text, nullable=True, comment="错误信息"),
        sa.Column("retry_count", sa.Integer, server_default="0", comment="已重试次数"),
        sa.Column("max_retries", sa.Integer, server_default="3", comment="最大重试次数"),
        sa.Column("next_retry_at", sa.DateTime, nullable=True, comment="下次重试时间"),
        sa.Column("sent_at", sa.DateTime, nullable=True, comment="实际发送时间"),
        sa.Column("extra_data", sa.JSON, nullable=True, comment="额外数据"),
        sa.Column("legacy_log_id", sa.String(36), nullable=True, comment="旧表 notification_logs.id"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_notification_deliveries_group_id", "notification_deliveries", ["group_id"])
    op.create_index("ix_notification_deliveries_recipient_id", "notification_deliveries", ["recipient_id"])
    op.create_index("ix_notification_deliveries_tenant_id", "notification_deliveries", ["tenant_id"])
    op.create_index("ix_notification_deliveries_channel", "notification_deliveries", ["channel"])
    op.create_index("ix_notification_deliveries_status", "notification_deliveries", ["status"])

    # --- unified_templates ---
    op.create_table(
        "unified_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, comment="租户ID"),
        sa.Column("code", sa.String(50), nullable=False, comment="模板编码"),
        sa.Column("name", sa.String(100), nullable=False, comment="模板名称"),
        sa.Column("message_type", sa.String(30), nullable=False, comment="消息类型"),
        sa.Column("event_type", sa.String(50), nullable=True, comment="事件类型"),
        sa.Column("subject_template", sa.String(200), nullable=True, comment="邮件主题模板"),
        sa.Column("html_template", sa.Text, nullable=True, comment="邮件 HTML 模板"),
        sa.Column("text_template", sa.Text, nullable=True, comment="纯文本模板"),
        sa.Column("wechat_template_id", sa.String(50), nullable=True, comment="微信模板 ID"),
        sa.Column("wechat_template_mapping", sa.JSON, nullable=True, comment="微信字段映射"),
        sa.Column("variables_schema", sa.JSON, nullable=True, comment="变量定义"),
        sa.Column("status", sa.Integer, server_default="1", comment="状态"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "code", name="uq_unified_template_tenant_code"),
    )
    op.create_index("ix_unified_templates_tenant_id", "unified_templates", ["tenant_id"])

    # --- channel_strategies ---
    op.create_table(
        "channel_strategies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, comment="租户ID"),
        sa.Column("event_type", sa.String(50), nullable=False, comment="事件类型"),
        sa.Column("channels", sa.JSON, nullable=False, comment="渠道列表"),
        sa.Column("strategy", sa.String(20), server_default="fallback", comment="策略"),
        sa.Column("dedup_window_seconds", sa.Integer, server_default="0", comment="去重窗口(秒)"),
        sa.Column("priority", sa.String(10), server_default="medium", comment="优先级"),
        sa.Column("quiet_hours_exempt", sa.Boolean, server_default="false", comment="豁免静默时段"),
        sa.Column("status", sa.Integer, server_default="1", comment="状态"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "event_type", name="uq_channel_strategy_tenant_event"),
    )
    op.create_index("ix_channel_strategies_tenant_id", "channel_strategies", ["tenant_id"])

    # --- recipient_rules ---
    op.create_table(
        "recipient_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, comment="租户ID"),
        sa.Column("name", sa.String(100), nullable=False, comment="规则名称"),
        sa.Column("rule_type", sa.String(30), nullable=False, comment="规则类型"),
        sa.Column("rule_config", sa.JSON, nullable=False, comment="规则配置"),
        sa.Column("event_type", sa.String(50), nullable=True, comment="绑定事件类型"),
        sa.Column("status", sa.Integer, server_default="1", comment="状态"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_recipient_rules_tenant_id", "recipient_rules", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("recipient_rules")
    op.drop_table("channel_strategies")
    op.drop_table("unified_templates")
    op.drop_table("notification_deliveries")
    op.drop_table("notification_recipients")
    op.drop_table("notification_groups")
