"""add name field to rule_windows

Revision ID: 047_add_rule_window_name
Revises: 046_tenant_schedule_suspensions
Create Date: 2026-03-29

为 rule_windows 表添加 name 字段，与前端时间窗配置保持一致。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '047_add_rule_window_name'
down_revision = '046_tenant_schedule_suspensions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加 name 列（允许 NULL，兼容历史数据）
    op.add_column('rule_windows', sa.Column('name', sa.String(200), nullable=True, comment='时间窗名称'))


def downgrade() -> None:
    # 删除列
    op.drop_column('rule_windows', 'name')
