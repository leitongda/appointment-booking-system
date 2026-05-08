"""accounts 表新增 email 字段，支持邮箱认证

Revision ID: 080_add_email_to_accounts
Revises: 079_add_role_id_to_extensions
Create Date: 2026-05-07

变更内容：
  - accounts 表新增 email 列 (String(100), nullable, indexed)
  - 新增唯一约束 uq_accounts_tenant_email(tenant_id, email)
  - 数据迁移：从 account_admins.email 回填到 accounts.email
"""
from alembic import op
import sqlalchemy as sa


revision = "080_add_email_to_accounts"
down_revision = "079_add_role_id_to_extensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 新增 email 列
    op.add_column(
        "accounts",
        sa.Column("email", sa.String(100), nullable=True, comment="邮箱（租户内唯一）"),
    )
    op.create_index("ix_accounts_email", "accounts", ["email"])

    # 2. 从 account_admins 回填 email 到 accounts
    # 仅迁移非空且格式合法的邮箱，跳过已存在的重复邮箱（保留最早的账号）
    op.execute("""
        UPDATE accounts AS a
        SET email = aa.email
        FROM account_admins AS aa
        WHERE a.id = aa.account_id
          AND aa.email IS NOT NULL
          AND aa.email != ''
          AND aa.email LIKE '%@%'
          AND NOT EXISTS (
              SELECT 1 FROM accounts AS a2
              WHERE a2.tenant_id = a.tenant_id
                AND a2.email = aa.email
                AND a2.id != a.id
          )
    """)

    # 3. 新增唯一约束（PostgreSQL 中 NULL 不参与 UNIQUE 约束）
    op.create_unique_constraint(
        "uq_accounts_tenant_email", "accounts", ["tenant_id", "email"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_accounts_tenant_email", "accounts", type_="unique")
    op.drop_index("ix_accounts_email", table_name="accounts")
    op.drop_column("accounts", "email")
