"""add appointment reminder columns

Revision ID: 012_appt_reminder
Revises: 011_merge_heads
Create Date: 2024-12-15 23:10:00.000000

Add reminder_sent and reminder_sent_at columns to appointments table.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '012_appt_reminder'
down_revision = '011_merge_heads'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(table_name: str, index_name: str) -> bool:
    """检查索引是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def upgrade() -> None:
    # 添加 reminder_sent 列
    if not column_exists('appointments', 'reminder_sent'):
        op.add_column('appointments', sa.Column('reminder_sent', sa.Integer, server_default='0', comment='是否已发送提醒: 0否 1是'))
    
    # 添加 reminder_sent_at 列
    if not column_exists('appointments', 'reminder_sent_at'):
        op.add_column('appointments', sa.Column('reminder_sent_at', sa.DateTime, nullable=True, comment='提醒发送时间'))
    
    # 创建提醒索引（用于 Celery 定时任务查询优化）
    if not index_exists('appointments', 'idx_appointments_reminder'):
        try:
            op.create_index('idx_appointments_reminder', 'appointments', ['status', 'reminder_sent', 'schedule_id'])
        except:
            pass


def downgrade() -> None:
    # 删除索引
    try:
        op.drop_index('idx_appointments_reminder', 'appointments')
    except:
        pass
    
    # 删除列
    if column_exists('appointments', 'reminder_sent_at'):
        op.drop_column('appointments', 'reminder_sent_at')
    
    if column_exists('appointments', 'reminder_sent'):
        op.drop_column('appointments', 'reminder_sent')

