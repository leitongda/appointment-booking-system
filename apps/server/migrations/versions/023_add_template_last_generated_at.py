"""add last_generated_at to schedule_templates

Revision ID: 023_last_generated_at
Revises: 022_add_schedule_generation_logs
Create Date: 2024-12-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '023_last_generated_at'
down_revision = '022_add_schedule_generation_logs'
branch_labels = None
depends_on = None


def upgrade():
    # 添加 last_generated_at 字段到 schedule_templates 表
    op.add_column(
        'schedule_templates',
        sa.Column('last_generated_at', sa.DateTime, nullable=True, comment='上一次生成排班时间')
    )


def downgrade():
    op.drop_column('schedule_templates', 'last_generated_at')

