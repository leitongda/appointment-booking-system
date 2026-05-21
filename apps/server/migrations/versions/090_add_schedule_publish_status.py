"""Add schedule_status and publish_status columns to schedules

Revision ID: 090_add_schedule_publish_status
Revises: 089_add_unique_constraint_to_schedules
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa

revision = '090_add_schedule_publish_status'
down_revision = '089_add_unique_constraint_to_schedules'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns as nullable first (safe for existing rows before backfill)
    op.add_column(
        'schedules',
        sa.Column(
            'schedule_status',
            sa.String(20),
            nullable=True,
            server_default='published',
            comment='排班状态: draft/published/booking/full/suspended/finished/withdrawn',
        ),
    )
    op.add_column(
        'schedules',
        sa.Column(
            'publish_status',
            sa.String(20),
            nullable=True,
            server_default='published',
            comment='发布状态: draft/published/withdrawn',
        ),
    )

    # Create indexes for efficient filtering
    op.create_index('ix_schedules_schedule_status', 'schedules', ['schedule_status'])
    op.create_index('ix_schedules_publish_status', 'schedules', ['publish_status'])


def downgrade() -> None:
    op.drop_index('ix_schedules_publish_status', table_name='schedules')
    op.drop_index('ix_schedules_schedule_status', table_name='schedules')
    op.drop_column('schedules', 'publish_status')
    op.drop_column('schedules', 'schedule_status')
