"""add tags and log_retention_days to tenants

Revision ID: 075_add_tags_log_retention
Revises: 074_add_password_policy_to_tenants
Create Date: 2026-04-28
"""
from alembic import op
import sqlalchemy as sa

revision = '075_add_tags_log_retention'
down_revision = '074_add_password_policy_to_tenants'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tenants', sa.Column('tags', sa.Text(), nullable=True, comment='租户标签(JSON数组)'))
    op.add_column('tenants', sa.Column(
        'log_retention_days', sa.Integer(),
        nullable=True, server_default='90',
        comment='日志保留天数(默认90)'
    ))


def downgrade() -> None:
    op.drop_column('tenants', 'log_retention_days')
    op.drop_column('tenants', 'tags')
