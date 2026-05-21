"""Backfill tenant_id for doctor_booking_settings from stores

Revision ID: 088_backfill_tenant_id_for_booking_settings
Revises: 087
Create Date: 2026-05-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = '088_backfill_tenant_id_for_booking_settings'
down_revision = '087_add_tenant_id_to_doctor_booking_settings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Backfill tenant_id from stores table
    result = bind.execute(
        text("""
            UPDATE doctor_booking_settings dbs
            SET tenant_id = s.tenant_id
            FROM stores s
            WHERE dbs.store_id = s.id
              AND dbs.tenant_id IS NULL
              AND s.tenant_id IS NOT NULL
        """)
    )
    print(f"Backfilled tenant_id for {result.rowcount} doctor_booking_settings")

    # Set NOT NULL after backfill
    op.alter_column(
        'doctor_booking_settings',
        'tenant_id',
        existing_type=sa.String(36),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        'doctor_booking_settings',
        'tenant_id',
        existing_type=sa.String(36),
        nullable=True,
    )
    op.execute(
        text("UPDATE doctor_booking_settings SET tenant_id = NULL")
    )
