"""添加三级提醒策略字段到预约表

Revision ID: 066_add_three_level_reminder_fields
Revises: 065_add_notification_log_indexes
Create Date: 2026-04-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '066_add_three_level_reminder_fields'
down_revision = '065_add_notification_log_indexes'
branch_labels = None
depends_on = None


def upgrade():
    """添加三级提醒字段"""

    # 添加三级提醒字段
    op.add_column(
        'appointments',
        sa.Column('reminder_sent_24h', sa.Integer(), nullable=False, server_default='0', comment='24h级别提醒是否已发送: 0否 1是')
    )
    op.add_column(
        'appointments',
        sa.Column('reminder_sent_2h', sa.Integer(), nullable=False, server_default='0', comment='2h级别提醒是否已发送: 0否 1是')
    )
    op.add_column(
        'appointments',
        sa.Column('reminder_sent_30min', sa.Integer(), nullable=False, server_default='0', comment='30min级别提醒是否已发送: 0否 1是')
    )

    # 更新现有 reminder_sent 字段注释，标记为兼容旧版本
    op.execute(
        "COMMENT ON COLUMN appointments.reminder_sent IS '是否已发送提醒: 0否 1是（兼容旧版本，对应24h级别）'"
    )
    op.execute(
        "COMMENT ON COLUMN appointments.reminder_sent_at IS '提醒发送时间（兼容旧版本）'"
    )

    # 数据迁移：将现有的 reminder_sent=1 的记录同步到 reminder_sent_24h
    op.execute(
        "UPDATE appointments SET reminder_sent_24h = 1 WHERE reminder_sent = 1"
    )

    # 创建索引以提高查询效率
    op.create_index(
        'ix_appointments_reminder_24h',
        'appointments',
        ['tenant_id', 'reminder_sent_24h']
    )
    op.create_index(
        'ix_appointments_reminder_2h',
        'appointments',
        ['tenant_id', 'reminder_sent_2h']
    )
    op.create_index(
        'ix_appointments_reminder_30min',
        'appointments',
        ['tenant_id', 'reminder_sent_30min']
    )


def downgrade():
    """移除三级提醒字段"""

    # 删除索引
    op.drop_index('ix_appointments_reminder_30min', table_name='appointments')
    op.drop_index('ix_appointments_reminder_2h', table_name='appointments')
    op.drop_index('ix_appointments_reminder_24h', table_name='appointments')

    # 删除字段
    op.drop_column('appointments', 'reminder_sent_30min')
    op.drop_column('appointments', 'reminder_sent_2h')
    op.drop_column('appointments', 'reminder_sent_24h')

    # 恢复原有注释
    op.execute(
        "COMMENT ON COLUMN appointments.reminder_sent IS '是否已发送提醒: 0否 1是'"
    )
