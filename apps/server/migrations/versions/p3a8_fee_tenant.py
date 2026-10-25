"""P3-8: consultation_fees / store_email_recipients 补租户列（数据模型项）

Revision ID: p3a8_fee_tenant
Revises: p3a7_settings_tenant
Create Date: 2026-10-24

计划 docs/tenant-remaining-plan.md §8 的遗留数据模型项：诊费与门店邮件接收人
两类表此前没有 tenant_id 列，只能靠 store 关联间接隔离。

- 5 张表 ADD COLUMN tenant_id（nullable + index）；
- 回填：经 store_id → stores.tenant_id；consultation_fee_templates 经
  fee_type_id → consultation_fee_types.store_id → stores.tenant_id
  （fee_type 为平台级时保持 NULL）；
- 逐表 ADD CONSTRAINT fk_<table>_tenant NOT VALID（复刻 p3a6 配方，
  VALIDATE 与孤儿清洗上线后按 scripts/m6_post_deploy_cleanse_and_validate.sql
  同款流程执行）；
- consultation_fee_types / consultation_fee_templates 的 NULL 保留平台级语义
  （store_id IS NULL = 全局类型/全局模板），与 news/banners 等内容表一致。

查询侧的锚点收口（service 按租户过滤 + 平台级 OR 分支）留待后续模块批次，
本迁移只落数据维度与外键保护；写入侧由 service 层落锚（create 时从 store 继承）。
"""
import sqlalchemy as sa
from alembic import op

revision = "p3a8_fee_tenant"
down_revision = "p3a7_settings_tenant"
branch_labels = None
depends_on = None

# (表, 回填 SQL)；SQL 用显式 JOIN 而非子查询，避免大表重复扫描
STORE_BACKFILL = (
    "UPDATE {table} SET tenant_id = stores.tenant_id "
    "FROM stores WHERE {table}.store_id = stores.id AND {table}.tenant_id IS NULL"
)

TABLES = (
    "consultation_fee_types",
    "consultation_fee_templates",
    "store_fee_templates",
    "doctor_consultation_fees",
    "store_email_recipients",
)


def upgrade() -> None:
    for table_name in TABLES:
        op.add_column(
            table_name,
            sa.Column(
                "tenant_id",
                sa.String(36),
                nullable=True,
                comment="租户ID",
            ),
        )
        op.create_index(
            f"ix_{table_name}_tenant_id", table_name, ["tenant_id"]
        )

    # 1) 有 store_id 的四张表直接回填
    for table_name in (
        "consultation_fee_types",
        "store_fee_templates",
        "doctor_consultation_fees",
        "store_email_recipients",
    ):
        op.execute(STORE_BACKFILL.format(table=table_name))

    # 2) 全局模板经 fee_type → store 回填（fee_type 平台级时保持 NULL）
    op.execute(
        "UPDATE consultation_fee_templates t SET tenant_id = ft.tenant_id "
        "FROM consultation_fee_types ft "
        "WHERE t.fee_type_id = ft.id AND t.tenant_id IS NULL"
    )

    # 3) 外键保护（NOT VALID，存量校验留待 M6 流程）
    for table_name in TABLES:
        op.create_foreign_key(
            f"fk_{table_name}_tenant",
            table_name,
            "tenants",
            ["tenant_id"],
            ["id"],
            postgresql_not_valid=True,
        )


def downgrade() -> None:
    for table_name in TABLES:
        op.drop_constraint(f"fk_{table_name}_tenant", table_name, type_="foreignkey")
        op.drop_index(f"ix_{table_name}_tenant_id", table_name=table_name)
        op.drop_column(table_name, "tenant_id")
