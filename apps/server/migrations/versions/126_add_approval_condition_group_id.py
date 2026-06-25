"""add group_id to approval_flow_conditions

Revision ID: 126_add_approval_condition_group_id
Revises: 125_fix_doctor_consultation_fees
Create Date: 2026-06-25

为审批流条件表添加 group_id 字段，支持条件组（组内 AND，组间 OR）。
"""
import sqlalchemy as sa
from alembic import op

revision = "126_add_approval_condition_group_id"
down_revision = "125_fix_doctor_consultation_fees"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "approval_flow_conditions",
        sa.Column("group_id", sa.String(50), nullable=True, comment="条件组 ID: 同组 AND，不同组 OR"),
    )


def downgrade() -> None:
    op.drop_column("approval_flow_conditions", "group_id")
