"""add notification_logs table

Revision ID: 058_add_notification_logs
Revises: 057_add_booked_slots_check_constraint
Create Date: 2026-04-18 17:15:00.000000
"""

from alembic import op
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON
import uuid
from datetime import datetime


revision = "058_add_notification_logs"
down_revision = "057_add_booked_slots_check_constraint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_logs",
        Column("id", String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        Column("tenant_id", String(36), nullable=True, comment="租户ID"),
        Column("store_id", String(36), nullable=True, comment="门店ID"),
        Column("user_id", String(36), nullable=True, comment="接收用户ID"),
        Column("user_type", String(20), nullable=True, comment="用户类型: patient/doctor/admin"),
        Column("channel", String(20), nullable=False, comment="通知通道: sms/email/in_app/wechat"),
        Column("message_type", String(30), nullable=True, comment="消息类型: appointment/schedule/system等"),
        Column("title", String(200), nullable=True, comment="消息标题"),
        Column("content", Text, nullable=True, comment="消息内容"),
        Column("status", String(20), nullable=False, default="pending", comment="发送状态: pending/sent/failed"),
        Column("error_message", Text, nullable=True, comment="错误信息"),
        Column("recipient", String(200), nullable=True, comment="接收人标识: 手机号/邮箱/openid"),
        Column("related_id", String(36), nullable=True, comment="关联业务ID"),
        Column("retry_count", Integer, default=0, comment="重试次数"),
        Column("sent_at", DateTime, nullable=True, comment="实际发送时间"),
        Column("created_at", DateTime, default=datetime.utcnow, comment="创建时间"),
        Column("extra_data", JSON, nullable=True, comment="额外数据"),
    )
    op.create_index("ix_notification_logs_tenant_id", "notification_logs", ["tenant_id"])
    op.create_index("ix_notification_logs_store_id", "notification_logs", ["store_id"])
    op.create_index("ix_notification_logs_user_id", "notification_logs", ["user_id"])
    op.create_index("ix_notification_logs_channel", "notification_logs", ["channel"])
    op.create_index("ix_notification_logs_status", "notification_logs", ["status"])


def downgrade() -> None:
    op.drop_table("notification_logs")
