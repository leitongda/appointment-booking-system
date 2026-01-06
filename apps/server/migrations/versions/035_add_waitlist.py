"""add waitlist table

Revision ID: 035_add_waitlist
Revises: 034_add_rule_management
Create Date: 2025-01-06 22:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '035_add_waitlist'
down_revision = '034_add_rule_management'
branch_labels = None
depends_on = None


def upgrade():
    """创建候补队列表"""
    op.create_table(
        'waitlist_entries',
        sa.Column('id', sa.String(36), primary_key=True, comment='候补ID'),
        sa.Column('user_id', sa.String(36), nullable=False, comment='用户ID'),
        sa.Column('patient_id', sa.String(36), nullable=False, comment='就诊人ID'),
        sa.Column('schedule_id', sa.String(36), nullable=False, comment='排班ID'),
        sa.Column('shift_type_id', sa.String(36), nullable=True, comment='班次类型ID'),
        sa.Column('status', sa.String(20), nullable=False, server_default='WAITING', comment='状态: WAITING-等待中, PROMOTED-已转预约, CANCELLED-已取消, EXPIRED-已过期'),
        sa.Column('position', sa.Integer, nullable=False, comment='在队列中的位置'),
        sa.Column('priority', sa.Integer, nullable=False, server_default='100', comment='优先级'),
        sa.Column('symptom_description', sa.String(500), nullable=True, comment='症状描述'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='加入候补时间'),
        sa.Column('promoted_at', sa.DateTime(), nullable=True, comment='转预约时间'),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True, comment='取消时间'),
        sa.Column('operator_id', sa.String(36), nullable=True, comment='操作人ID'),
        sa.Column('operator_type', sa.String(20), nullable=True, comment='操作人类型: USER/ADMIN/SYSTEM'),
        sa.Column('created_by', sa.String(36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(36), nullable=True, comment='更新人ID'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.text('CURRENT_TIMESTAMP')),
    )
    # 创建索引
    op.create_index('ix_waitlist_user_id', 'waitlist_entries', ['user_id'])
    op.create_index('ix_waitlist_schedule_id', 'waitlist_entries', ['schedule_id'])
    op.create_index('ix_waitlist_schedule_status', 'waitlist_entries', ['schedule_id', 'status'])
    op.create_index('ix_waitlist_created_at', 'waitlist_entries', ['created_at'])
    op.create_index('ix_waitlist_position', 'waitlist_entries', ['schedule_id', 'position'])


def downgrade():
    """删除候补队列表"""
    op.drop_index('ix_waitlist_position', table_name='waitlist_entries')
    op.drop_index('ix_waitlist_created_at', table_name='waitlist_entries')
    op.drop_index('ix_waitlist_schedule_status', table_name='waitlist_entries')
    op.drop_index('ix_waitlist_schedule_id', table_name='waitlist_entries')
    op.drop_index('ix_waitlist_user_id', table_name='waitlist_entries')
    op.drop_table('waitlist_entries')
