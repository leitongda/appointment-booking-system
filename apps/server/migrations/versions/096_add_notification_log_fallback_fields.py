"""Add fallback tracking fields to notification_logs

Revision ID: 096_add_notification_log_fallback_fields
Revises: 095_create_schedule_holidays
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa


revision = '096_add_notification_log_fallback_fields'
down_revision = '095_create_schedule_holidays'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 降级场景下的首选渠道记录
    op.add_column('notification_logs', sa.Column(
        'primary_channel', sa.String(20), nullable=True,
        comment='首选渠道（降级场景下记录原始目标渠道）'
    ))
    # 降级原因
    op.add_column('notification_logs', sa.Column(
        'fallback_reason', sa.String(200), nullable=True,
        comment='降级原因（如: 渠道不可用/发送失败/API异常）'
    ))
    # 当前渠道在降级链中的尝试顺序
    op.add_column('notification_logs', sa.Column(
        'channel_attempt_order', sa.Integer(), nullable=True,
        comment='当前渠道在降级链中的尝试顺序（0=首选渠道）'
    ))
    # 为降级查询创建索引
    op.create_index(
        'ix_notification_logs_primary_channel',
        'notification_logs',
        ['primary_channel'],
    )


def downgrade() -> None:
    op.drop_index('ix_notification_logs_primary_channel', table_name='notification_logs')
    op.drop_column('notification_logs', 'channel_attempt_order')
    op.drop_column('notification_logs', 'fallback_reason')
    op.drop_column('notification_logs', 'primary_channel')
