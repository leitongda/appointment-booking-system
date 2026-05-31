"""create freelance fee tables

Revision ID: 119
Revises: 117
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '119'
down_revision = '117'
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not table_exists('freelance_freelancers'):
        op.create_table(
            'freelance_freelancers',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True),
            sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=True, index=True),
            sa.Column('name', sa.String(50), nullable=False),
            sa.Column('phone', sa.String(20), nullable=True),
            sa.Column('account_name', sa.String(100), nullable=True),
            sa.Column('account_platform', sa.String(20), server_default='xiaohongshu'),
            sa.Column('account_type', sa.String(20), server_default='old'),
            sa.Column('status', sa.Integer, server_default='1'),
            sa.Column('remark', sa.Text, nullable=True),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('created_by', sa.String(36), nullable=True),
            sa.Column('updated_by', sa.String(36), nullable=True),
        )

    if not table_exists('freelance_tasks'):
        op.create_table(
            'freelance_tasks',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True),
            sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=True, index=True),
            sa.Column('freelancer_id', sa.String(36), sa.ForeignKey('freelance_freelancers.id'), nullable=False, index=True),
            sa.Column('title', sa.String(200), nullable=False),
            sa.Column('content_url', sa.String(500), nullable=True),
            sa.Column('published_at', sa.DateTime, nullable=True),
            sa.Column('status', sa.String(20), server_default='pending'),
            sa.Column('is_indexed', sa.Boolean, server_default='false'),
            sa.Column('likes_count', sa.Integer, server_default='0'),
            sa.Column('comments_count', sa.Integer, server_default='0'),
            sa.Column('base_amount', sa.Numeric(10, 2), server_default='5'),
            sa.Column('bonus_amount', sa.Numeric(10, 2), server_default='0'),
            sa.Column('likes_bonus_amount', sa.Numeric(10, 2), server_default='0'),
            sa.Column('planned_base_settle_at', sa.DateTime, nullable=True),
            sa.Column('planned_bonus_settle_at', sa.DateTime, nullable=True),
            sa.Column('planned_likes_settle_at', sa.DateTime, nullable=True),
            sa.Column('remark', sa.Text, nullable=True),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('created_by', sa.String(36), nullable=True),
            sa.Column('updated_by', sa.String(36), nullable=True),
        )

    if not table_exists('freelance_interactions'):
        op.create_table(
            'freelance_interactions',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True),
            sa.Column('task_id', sa.String(36), sa.ForeignKey('freelance_tasks.id'), nullable=False, index=True),
            sa.Column('interaction_type', sa.String(20), nullable=False),
            sa.Column('content', sa.Text, nullable=True),
            sa.Column('amount', sa.Numeric(10, 2), server_default='0.5'),
            sa.Column('interacted_at', sa.DateTime, nullable=True),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('created_by', sa.String(36), nullable=True),
            sa.Column('updated_by', sa.String(36), nullable=True),
        )

    if not table_exists('freelance_settlements'):
        op.create_table(
            'freelance_settlements',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True),
            sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=True, index=True),
            sa.Column('freelancer_id', sa.String(36), sa.ForeignKey('freelance_freelancers.id'), nullable=False, index=True),
            sa.Column('settlement_no', sa.String(32), unique=True, nullable=False),
            sa.Column('period_start', sa.DateTime, nullable=True),
            sa.Column('period_end', sa.DateTime, nullable=True),
            sa.Column('base_total', sa.Numeric(10, 2), server_default='0'),
            sa.Column('bonus_total', sa.Numeric(10, 2), server_default='0'),
            sa.Column('likes_bonus_total', sa.Numeric(10, 2), server_default='0'),
            sa.Column('interaction_total', sa.Numeric(10, 2), server_default='0'),
            sa.Column('total_amount', sa.Numeric(10, 2), server_default='0'),
            sa.Column('tax_amount', sa.Numeric(10, 2), server_default='0'),
            sa.Column('actual_amount', sa.Numeric(10, 2), server_default='0'),
            sa.Column('status', sa.String(20), server_default='pending'),
            sa.Column('confirmed_at', sa.DateTime, nullable=True),
            sa.Column('confirmed_by', sa.String(36), nullable=True),
            sa.Column('paid_at', sa.DateTime, nullable=True),
            sa.Column('reject_reason', sa.Text, nullable=True),
            sa.Column('remark', sa.Text, nullable=True),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('created_by', sa.String(36), nullable=True),
            sa.Column('updated_by', sa.String(36), nullable=True),
        )

    if not table_exists('freelance_settlement_items'):
        op.create_table(
            'freelance_settlement_items',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('settlement_id', sa.String(36), sa.ForeignKey('freelance_settlements.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('item_type', sa.String(20), nullable=False),
            sa.Column('task_id', sa.String(36), sa.ForeignKey('freelance_tasks.id'), nullable=True),
            sa.Column('interaction_id', sa.String(36), sa.ForeignKey('freelance_interactions.id'), nullable=True),
            sa.Column('description', sa.String(200), nullable=True),
            sa.Column('amount', sa.Numeric(10, 2), server_default='0'),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table('freelance_settlement_items')
    op.drop_table('freelance_settlements')
    op.drop_table('freelance_interactions')
    op.drop_table('freelance_tasks')
    op.drop_table('freelance_freelancers')
