"""Backfill shift_type_id for historical schedule_templates

Revision ID: 083_backfill_shift_type_id_for_templates
Revises: 082_add_shift_type_to_schedule_templates
Create Date: 2026-05-12

For existing schedule_templates without shift_type_id, assign the first
enabled ShiftType within the same tenant. If no ShiftType exists for
that tenant, leave shift_type_id as NULL.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = "083_backfill_shift_type_id_for_templates"
down_revision = "082_add_shift_type_to_schedule_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    result = bind.execute(
        text("""
            UPDATE schedule_templates st
            SET shift_type_id = sub.first_shift_type_id
            FROM (
                SELECT DISTINCT ON (st2.tenant_id)
                    st2.id AS template_id,
                    ft.id AS first_shift_type_id
                FROM schedule_templates st2
                CROSS JOIN LATERAL (
                    SELECT id FROM shift_types
                    WHERE (shift_types.tenant_id = st2.tenant_id OR shift_types.tenant_id IS NULL)
                      AND shift_types.enabled = true
                    ORDER BY shift_types.tenant_id DESC NULLS LAST, shift_types.created_at ASC
                    LIMIT 1
                ) ft
                WHERE st2.shift_type_id IS NULL
            ) sub
            WHERE st.id = sub.template_id
              AND st.shift_type_id IS NULL
        """)
    )
    print(f"Backfilled shift_type_id for {result.rowcount} schedule_templates")


def downgrade() -> None:
    op.execute(
        text("UPDATE schedule_templates SET shift_type_id = NULL")
    )
