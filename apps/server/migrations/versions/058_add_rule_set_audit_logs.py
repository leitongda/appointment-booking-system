"""add rule_set_audit_logs table

Revision ID: 058_add_rule_set_audit_logs
Revises: 057_add_booked_slots_check_constraint
Create Date: 2026-04-18 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "058_add_rule_set_audit_logs"
down_revision = "057_add_booked_slots_check_constraint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rule_set_audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_set_id", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("operator_id", sa.String(36), nullable=True),
        sa.Column("snapshot_before", sa.Text, nullable=True),
        sa.Column("snapshot_after", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.create_index(
        "ix_rule_set_audit_logs_rule_set_id",
        "rule_set_audit_logs",
        ["rule_set_id"],
    )
    op.create_index(
        "ix_rule_set_audit_logs_tenant_id",
        "rule_set_audit_logs",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_rule_set_audit_logs_tenant_id", table_name="rule_set_audit_logs")
    op.drop_index("ix_rule_set_audit_logs_rule_set_id", table_name="rule_set_audit_logs")
    op.drop_table("rule_set_audit_logs")
