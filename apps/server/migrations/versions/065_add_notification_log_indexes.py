"""添加通知日志索引以支持用量统计

Revision ID: 065_add_notification_log_indexes
Revises: 064
Create Date: 2026-04-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '065_add_notification_log_indexes'
down_revision = '064'
branch_labels = None
depends_on = None


def upgrade():
    """添加复合索引以支持高效的通知用量统计查询"""

    # 租户 + 通道 + 状态 + 发送时间的复合索引
    # 用于查询：某租户在某渠道的成功发送数量（配额检查）
    op.create_index(
        'ix_notification_logs_tenant_channel_status_sent_at',
        'notification_logs',
        ['tenant_id', 'channel', 'status', 'sent_at']
    )

    # 租户 + 创建时间的索引（用于日期范围查询）
    op.create_index(
        'ix_notification_logs_tenant_created_at',
        'notification_logs',
        ['tenant_id', 'created_at']
    )

    # 用于每日趋势查询的索引：租户 + 日期（created_at）
    # 注：PostgreSQL 可以使用函数索引
    # op.create_index(
    #     'ix_notification_logs_tenant_date',
    #     'notification_logs',
    #     [sa.text('tenant_id'), sa.text('date(created_at)')],
    #     postgresql_concurrently=True
    # )


def downgrade():
    """移除添加的索引"""
    op.drop_index('ix_notification_logs_tenant_channel_status_sent_at', table_name='notification_logs')
    op.drop_index('ix_notification_logs_tenant_created_at', table_name='notification_logs')