"""Add notification_preferences table

Revision ID: 060_add_notification_preferences
Revises: 059_add_tenant_id_to_template_tables
Create Date: 2026-04-18 20:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "060_add_notification_preferences"
down_revision = "059_add_tenant_id_to_template_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=True, comment="租户ID"),
        sa.Column("user_id", sa.String(36), nullable=False, comment="用户ID"),
        sa.Column("user_type", sa.String(20), nullable=False, comment="用户类型: patient/doctor"),
        sa.Column("appointment_enabled", sa.Boolean(), nullable=True, comment="预约通知"),
        sa.Column("reminder_enabled", sa.Boolean(), nullable=True, comment="就诊提醒"),
        sa.Column("queue_call_enabled", sa.Boolean(), nullable=True, comment="叫号通知"),
        sa.Column("stop_clinic_enabled", sa.Boolean(), nullable=True, comment="停诊通知"),
        sa.Column("system_enabled", sa.Boolean(), nullable=True, comment="系统通知"),
        sa.Column("sms_enabled", sa.Boolean(), nullable=True, comment="短信通知"),
        sa.Column("email_enabled", sa.Boolean(), nullable=True, comment="邮件通知"),
        sa.Column("wechat_enabled", sa.Boolean(), nullable=True, comment="微信推送"),
        sa.Column("in_app_enabled", sa.Boolean(), nullable=True, comment="站内消息"),
        sa.Column("quiet_hours_start", sa.String(5), nullable=True, comment="免打扰开始时间 HH:MM"),
        sa.Column("quiet_hours_end", sa.String(5), nullable=True, comment="免打扰结束时间 HH:MM"),
        sa.Column("created_at", sa.DateTime(), nullable=True, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=True, comment="更新时间"),
    )
    op.create_index("ix_notification_preferences_tenant_id", "notification_preferences", ["tenant_id"])
    op.create_index("ix_notification_preferences_user_id", "notification_preferences", ["user_id"])
    op.create_unique_constraint("uq_notification_pref_user", "notification_preferences", ["user_id", "user_type"])


def downgrade() -> None:
    op.drop_constraint("uq_notification_pref_user", "notification_preferences", type_="unique")
    op.drop_index("ix_notification_preferences_user_id", table_name="notification_preferences")
    op.drop_index("ix_notification_preferences_tenant_id", table_name="notification_preferences")
    op.drop_table("notification_preferences")
