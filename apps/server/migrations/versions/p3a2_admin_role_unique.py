"""P3-2: admins.username / roles.code become tenant-scoped unique

Revision ID: p3a2_admin_role_unique
Revises: p3a1_content_tenant
Create Date: 2026-10-23

- admins.username / roles.code 改为 (tenant_id, col) 唯一；
- tenant_id IS NULL 的平台行用 partial unique index 保持唯一；
- admins.username 原为全局唯一，故不存在跨租户重复；roles.code 若同租户内
  已有重复，create_unique_constraint 会直接失败并指出冲突（先按 D13 清理后重跑）。
downgrade 恢复全局唯一；若已存在跨租户同名行会失败，需先清理。
"""
import sqlalchemy as sa
from alembic import op

revision = "p3a2_admin_role_unique"
down_revision = "p3a1_content_tenant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("admins_username_key", "admins", type_="unique")
    op.create_unique_constraint(
        "uq_admins_tenant_username", "admins", ["tenant_id", "username"]
    )
    op.create_index(
        "uq_admins_username_platform",
        "admins",
        ["username"],
        unique=True,
        postgresql_where=sa.text("tenant_id IS NULL"),
    )

    op.create_unique_constraint("uq_roles_tenant_code", "roles", ["tenant_id", "code"])
    op.create_index(
        "uq_roles_code_platform",
        "roles",
        ["code"],
        unique=True,
        postgresql_where=sa.text("tenant_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_roles_code_platform", table_name="roles")
    op.drop_constraint("uq_roles_tenant_code", "roles", type_="unique")
    op.drop_index("uq_admins_username_platform", table_name="admins")
    op.drop_constraint("uq_admins_tenant_username", "admins", type_="unique")
    op.create_unique_constraint("admins_username_key", "admins", ["username"])
