"""add schedule_generation_logs table

Revision ID: 022_add_schedule_generation_logs
Revises: 021_merge_custom_schedules
Create Date: 2024-12-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '022_add_schedule_generation_logs'
down_revision = '021_merge_custom_schedules'
branch_labels = None
depends_on = None


def upgrade():
    # 创建排班生成日志表
    op.create_table(
        'schedule_generation_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('template_id', sa.String(36), sa.ForeignKey('schedule_templates.id', ondelete='CASCADE'), nullable=False, comment='排班规则ID'),
        sa.Column('operator_id', sa.String(36), sa.ForeignKey('admins.id', ondelete='SET NULL'), nullable=True, comment='操作人ID'),
        sa.Column('operator_name', sa.String(100), nullable=True, comment='操作人姓名'),
        sa.Column('action_type', sa.String(20), nullable=False, comment='操作类型: generate/delete/suspend'),
        sa.Column('start_date', sa.Date, nullable=True, comment='开始日期'),
        sa.Column('end_date', sa.Date, nullable=True, comment='结束日期'),
        sa.Column('affected_count', sa.Integer, default=0, comment='影响的记录数'),
        sa.Column('remark', sa.Text, nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    
    # 创建索引
    op.create_index('idx_schedule_generation_logs_template_id', 'schedule_generation_logs', ['template_id'])
    op.create_index('idx_schedule_generation_logs_created_at', 'schedule_generation_logs', ['created_at'])


def downgrade():
    op.drop_index('idx_schedule_generation_logs_created_at')
    op.drop_index('idx_schedule_generation_logs_template_id')
    op.drop_table('schedule_generation_logs')

