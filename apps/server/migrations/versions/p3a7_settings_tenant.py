"""P3-7: system_settings tenant dimension + tenant child-table indexes

Revision ID: p3a7_settings_tenant
Revises: p3a6_tenant_fk
Create Date: 2026-10-23

- system_settings 增加 tenant_id（NULL=平台级）与 (tenant_id, category) 索引；
- tenant_subscriptions / tenant_notifications 的 tenant_id 补索引。
本期不改变任何读写路径；第4期再实现「租户覆盖 → 门店覆盖 → 平台默认」三级解析，
微信/短信配置读点届时改为按租户读取。
downgrade 对称删除，无数据风险。
"""
import sqlalchemy as sa
from alembic import op

revision = "p3a7_settings_tenant"
down_revision = "p3a6_tenant_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "system_settings",
        sa.Column("tenant_id", sa.String(36), nullable=True, comment="租户ID，NULL表示平台级配置"),
    )
    op.create_index(
        "ix_system_settings_tenant_id", "system_settings", ["tenant_id"]
    )
    op.create_index(
        "ix_system_settings_tenant_category", "system_settings", ["tenant_id", "category"]
    )

    op.create_index(
        "ix_tenant_subscriptions_tenant_id", "tenant_subscriptions", ["tenant_id"]
    )
    op.create_index(
        "ix_tenant_notifications_tenant_id", "tenant_notifications", ["tenant_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_notifications_tenant_id", table_name="tenant_notifications")
    op.drop_index("ix_tenant_subscriptions_tenant_id", table_name="tenant_subscriptions")
    op.drop_index("ix_system_settings_tenant_category", table_name="system_settings")
    op.drop_index("ix_system_settings_tenant_id", table_name="system_settings")
    op.drop_column("system_settings", "tenant_id")
