"""add rate limit fields to tenants

Revision ID: 104
Revises: 103
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = '104'
down_revision = '103'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tenants', sa.Column('rate_limit_per_minute', sa.Integer(), nullable=True, comment='每分钟请求上限（覆盖全局 300）'))
    op.add_column('tenants', sa.Column('rate_limit_per_second', sa.Integer(), nullable=True, comment='每秒请求上限（覆盖全局 50）'))


def downgrade() -> None:
    op.drop_column('tenants', 'rate_limit_per_second')
    op.drop_column('tenants', 'rate_limit_per_minute')
