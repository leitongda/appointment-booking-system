"""add tenant_id to blacklists

Revision ID: 054_add_tenant_id_to_blacklists
Revises: 053_add_refund_records_table
Create Date: 2026-04-17 18:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "054_add_tenant_id_to_blacklists"
down_revision = "053_add_refund_records_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "blacklists",
        sa.Column("tenant_id", sa.String(length=36), nullable=True, comment="租户ID"),
    )
    op.create_foreign_key(
        "fk_blacklists_tenant_id_tenants",
        "blacklists",
        "tenants",
        ["tenant_id"],
        ["id"],
    )
    op.create_index("ix_blacklists_tenant_id", "blacklists", ["tenant_id"])

    op.execute(
        """
        UPDATE blacklists AS b
        SET tenant_id = u.tenant_id
        FROM users AS u
        WHERE b.user_id = u.id
          AND b.tenant_id IS NULL
        """
    )

    op.execute(
        """
        UPDATE blacklists AS b
        SET tenant_id = s.tenant_id
        FROM stores AS s
        WHERE b.store_id = s.id
          AND b.tenant_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_blacklists_tenant_id", table_name="blacklists")
    op.drop_constraint("fk_blacklists_tenant_id_tenants", "blacklists", type_="foreignkey")
    op.drop_column("blacklists", "tenant_id")
