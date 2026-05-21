"""Add composite unique constraint to schedules

Revision ID: 089_add_unique_constraint_to_schedules
Revises: 088
Create Date: 2026-05-20

"""
from alembic import op


revision = '089_add_unique_constraint_to_schedules'
down_revision = '088_backfill_tenant_id_for_booking_settings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        'uix_schedule_doctor_date_time',
        'schedules',
        ['doctor_id', 'schedule_date', 'start_time', 'end_time'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        'uix_schedule_doctor_date_time',
        'schedules',
    )
