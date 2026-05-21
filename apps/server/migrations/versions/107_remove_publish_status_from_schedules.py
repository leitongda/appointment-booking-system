"""remove publish_status from schedules (merged into schedule_status)

Revision ID: 107
Revises: 106
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = '107'
down_revision = '106'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('schedules', 'publish_status')


def downgrade() -> None:
    op.add_column('schedules', sa.Column(
        'publish_status', sa.String(20), nullable=False, server_default='published',
        comment='发布状态: draft/published/withdrawn',
    ))
