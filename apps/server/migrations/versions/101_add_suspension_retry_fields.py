"""add suspension retry fields

Revision ID: 101
Revises: 100
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa

revision = '101'
down_revision = '100'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'schedule_suspensions',
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0', comment='处置重试次数'),
    )
    op.add_column(
        'schedule_suspensions',
        sa.Column('last_retry_at', sa.DateTime(), nullable=True, comment='上次重试时间'),
    )


def downgrade() -> None:
    op.drop_column('schedule_suspensions', 'last_retry_at')
    op.drop_column('schedule_suspensions', 'retry_count')
