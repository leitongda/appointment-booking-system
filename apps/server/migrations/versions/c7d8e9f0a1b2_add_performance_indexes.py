"""add performance indexes for statistics queries

Revision ID: c7d8e9f0a1b2
Revises: f1a2b3c4d5e6
Create Date: 2026-06-26 10:00:00.000000
"""
from alembic import op

# revision identifiers
revision = "c7d8e9f0a1b2"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # appointments: 加速按 status + created_at 的统计查询
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_appointments_status_created_at "
        "ON appointments(status, created_at)"
    )

    # user_behavior_logs: 加速按 event_type + created_at 的 PV/UV 查询
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_behavior_logs_event_type_created_at "
        "ON user_behavior_logs(event_type, created_at)"
    )

    # schedules: 加速按 date + doctor_id 的 JOIN 查询
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_schedules_date_doctor "
        "ON schedules(schedule_date, doctor_id)"
    )

    # doctor_consultation_fees: 加速诊费查询
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_dcf_doctor_fee_store_status "
        "ON doctor_consultation_fees(doctor_id, fee_type_id, store_id, status)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_dcf_doctor_fee_store_status")
    op.execute("DROP INDEX IF EXISTS idx_schedules_date_doctor")
    op.execute("DROP INDEX IF EXISTS idx_behavior_logs_event_type_created_at")
    op.execute("DROP INDEX IF EXISTS idx_appointments_status_created_at")
