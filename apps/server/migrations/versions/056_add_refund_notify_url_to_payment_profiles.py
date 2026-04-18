"""add refund notify url to payment profiles

Revision ID: 056_add_refund_notify_url_to_payment_profiles
Revises: 055_add_permission_control_type
Create Date: 2026-04-18 10:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "056_add_refund_notify_url_to_payment_profiles"
down_revision = "055_add_permission_control_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payment_profiles",
        sa.Column("refund_notify_url", sa.String(length=255), nullable=True, comment="退款回调地址"),
    )


def downgrade() -> None:
    op.drop_column("payment_profiles", "refund_notify_url")
