"""add password_policy to tenants

Revision ID: 074_add_password_policy_to_tenants
Revises: 073_add_support_tickets
Create Date: 2026-04-28
"""
from alembic import op
import sqlalchemy as sa


revision = '074_add_password_policy_to_tenants'
down_revision = '073_add_support_tickets'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'tenants',
        sa.Column('password_policy', sa.Text(), nullable=True, comment='密码策略(JSON)')
    )


def downgrade() -> None:
    op.drop_column('tenants', 'password_policy')
