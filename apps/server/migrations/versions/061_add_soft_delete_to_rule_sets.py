"""Add soft delete to rule_sets

Revision ID: 061_add_soft_delete_to_rule_sets
Revises: 060_add_notification_preferences
Create Date: 2026-04-27 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "061_add_soft_delete_to_rule_sets"
down_revision = "060_add_notification_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rule_sets",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间"),
    )
    op.drop_index("idx_rule_sets_enabled_priority", table_name="rule_sets")
    op.create_index(
        "idx_rule_sets_enabled_priority",
        "rule_sets",
        ["enabled", "priority", "deleted_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_rule_sets_enabled_priority", table_name="rule_sets")
    op.create_index(
        "idx_rule_sets_enabled_priority",
        "rule_sets",
        ["enabled", "priority"],
    )
    op.drop_column("rule_sets", "deleted_at")
