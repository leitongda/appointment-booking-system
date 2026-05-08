"""set tenant_id NOT NULL on core business tables

Revision ID: 043_tenant_id_not_null
Revises: 042_composite_indexes
Create Date: 2026-03-27

将核心业务表的 tenant_id 从 nullable=True 改为 nullable=False。
先回填 NULL 值再设 NOT NULL。
roles 表保留 nullable（平台角色 tenant_id 为 NULL）。
"""
import uuid
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
    # 确保默认订阅计划存在
    op.execute(sa.text("""
        INSERT INTO subscription_plans (
            id, plan_code, name, description,
            price_monthly, price_yearly, currency,
            max_stores, max_admins, max_doctors,
            max_appointments_per_month, max_storage_mb,
            status, is_default
        )
        VALUES (
            :plan_id, 'basic', '基础版', '默认基础计划',
            0, 0, 'CNY',
            10, 20, 100,
            5000, 5120,
            1, true
        )
        ON CONFLICT (plan_code) DO NOTHING
    """).bindparams(plan_id=str(uuid.uuid4())))

    # 确保默认租户存在
    op.execute(sa.text("""
        INSERT INTO tenants (
            id, tenant_code, name, status,
            subscription_plan_id, subscription_start_at, subscription_end_at,
            billing_cycle, contact_name
        )
        SELECT
            :tenant_id, 'default', '默认租户', 1,
            sp.id,
            NOW(), NOW() + INTERVAL '100 years',
            'yearly', '系统管理员'
        FROM subscription_plans sp
        WHERE sp.plan_code = 'basic'
          AND NOT EXISTS (SELECT 1 FROM tenants WHERE tenant_code = 'default')
        LIMIT 1
    """).bindparams(tenant_id=str(uuid.uuid4())))

    # 回填所有表中 tenant_id 为 NULL 的行，关联到默认租户
    for table, column in NOT_NULL_TABLES:
        op.execute(sa.text(
            f"UPDATE {table} SET tenant_id = "
            f"(SELECT id FROM tenants WHERE tenant_code = 'default' LIMIT 1) "
            f"WHERE tenant_id IS NULL"
        ))
    for table, column in NOT_NULL_TABLES:
        op.alter_column(table, column, nullable=False)


def downgrade() -> None:
    for table, column in NOT_NULL_TABLES:
        op.alter_column(table, column, nullable=True)
