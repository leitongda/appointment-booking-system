"""Backfill schedule_status and publish_status from existing status field

Revision ID: 091_backfill_schedule_publish_status
Revises: 090_add_schedule_publish_status
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa

revision = '091_backfill_schedule_publish_status'
down_revision = '090_add_schedule_publish_status'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backfill from existing status field
    # status=1 (正常) -> schedule_status='published', publish_status='published'
    # status=0 (停诊) -> schedule_status='suspended', publish_status='published'
    op.execute(
        "UPDATE schedules SET schedule_status = 'published', publish_status = 'published' "
        "WHERE status = 1 AND schedule_status IS NULL"
    )
    op.execute(
        "UPDATE schedules SET schedule_status = 'suspended', publish_status = 'published' "
        "WHERE status = 0 AND schedule_status IS NULL"
    )

    # Set NOT NULL on schedule_status after backfill is complete
    op.alter_column(
        'schedules', 'schedule_status',
        existing_type=sa.String(20),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        'schedules', 'schedule_status',
        existing_type=sa.String(20),
        nullable=True,
    )
