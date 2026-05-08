"""users 表新增 email 字段，支持邮箱认证

Revision ID: 081_add_email_to_users
Revises: 080_add_email_to_accounts
Create Date: 2026-05-07

变更内容：
  - users 表新增 email 列 (String(100), nullable, indexed)
  - 新增唯一约束 uq_users_tenant_email(tenant_id, email)
"""
from alembic import op
import sqlalchemy as sa


revision = "081_add_email_to_users"
down_revision = "080_add_email_to_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email", sa.String(100), nullable=True, comment="邮箱（租户内唯一）"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_unique_constraint(
        "uq_users_tenant_email", "users", ["tenant_id", "email"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_users_tenant_email", "users", type_="unique")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "email")
