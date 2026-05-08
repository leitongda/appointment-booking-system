"""set tenant_id NOT NULL on core business tables

Revision ID: 043_tenant_id_not_null
Revises: 042_composite_indexes
Create Date: 2026-03-27

将核心业务表的 tenant_id 从 nullable=True 改为 nullable=False。
先回填 NULL 值再设 NOT NULL。
roles 表保留 nullable（平台角色 tenant_id 为 NULL）。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '043_tenant_id_not_null'
down_revision = '042_composite_indexes'
branch_labels = None
depends_on = None

# (table, column) 需要设置为 NOT NULL 的表
NOT_NULL_TABLES = [
    ("stores", "tenant_id"),
    ("admins", "tenant_id"),
    ("users", "tenant_id"),
    ("patients", "tenant_id"),
    ("doctors", "tenant_id"),
    ("departments", "tenant_id"),
    ("schedules", "tenant_id"),
    ("schedule_templates", "tenant_id"),
    ("appointments", "tenant_id"),
]


def upgrade() -> None:
    # 回填所有表中 tenant_id 为 NULL 的行，关联到默认租户
    for table, column in NOT_NULL_TABLES:
        op.execute(
            f"UPDATE {table} SET tenant_id = "
            f"(SELECT id FROM tenants WHERE tenant_code = 'default' LIMIT 1) "
            f"WHERE tenant_id IS NULL"
        )
    for table, column in NOT_NULL_TABLES:
        op.alter_column(table, column, nullable=False)


def downgrade() -> None:
    for table, column in NOT_NULL_TABLES:
        op.alter_column(table, column, nullable=True)
