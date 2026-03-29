"""add tenant_id to schedule_suspensions

Revision ID: 046_tenant_schedule_suspensions
Revises: 045_add_tenant_soft_delete
Create Date: 2026-03-29

为 schedule_suspensions 表添加 tenant_id 字段，实现多租户隔离。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '046_tenant_schedule_suspensions'
down_revision = '045_add_tenant_soft_delete'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加 tenant_id 列（允许 NULL，兼容历史数据）
    op.add_column('schedule_suspensions', sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, comment='租户ID'))
    # 创建索引
    op.create_index('idx_schedule_suspensions_tenant_id', 'schedule_suspensions', ['tenant_id'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('idx_schedule_suspensions_tenant_id', 'schedule_suspensions')
    # 删除列
    op.drop_column('schedule_suspensions', 'tenant_id')
