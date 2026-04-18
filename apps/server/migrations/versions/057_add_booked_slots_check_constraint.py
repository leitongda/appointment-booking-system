"""add booked_slots non-negative check constraint

Revision ID: 057_add_booked_slots_check_constraint
Revises: 056_add_refund_notify_url_to_payment_profiles
Create Date: 2026-04-18 17:00:00.000000
"""

from alembic import op


revision = "057_add_booked_slots_check_constraint"
down_revision = "056_add_refund_notify_url_to_payment_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_schedules_booked_slots_non_negative",
        "schedules",
        "booked_slots >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_schedules_booked_slots_non_negative",
        "schedules",
        type_="check",
    )
