"""P3-6: bare tenant_id columns get foreign keys (NOT VALID)

Revision ID: p3a6_tenant_fk
Revises: p3a5_usage_daily_unique
Create Date: 2026-10-23

- rule_set_audit_logs / schedule_audit_logs 的 tenant_id 放宽为 nullable；
- 逐表 ADD CONSTRAINT ... NOT VALID（新写入立即受保护，不阻塞存量校验）。
- VALIDATE 与孤儿清洗为上线后手动步骤（见文件末尾 SQL），避免迁移期长锁；
  未执行前约束状态为 NOT VALID，属预期。

上线后手动执行——清洗配方必须按列的 NULL 约束分两类（R4-6），
完整可执行脚本见 scripts/m6_post_deploy_cleanse_and_validate.sql：

A. 可空表（10 张，tenant_id NULL 合法，孤儿可直接置 NULL）：
   email_templates / message_templates / notification_logs /
   notification_preferences / rule_set_audit_logs / schedule_audit_logs /
   news / notices / banners / content_versions
   UPDATE <table> SET tenant_id = NULL
    WHERE tenant_id IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM tenants WHERE tenants.id = <table>.tenant_id);
   ALTER TABLE <table> VALIDATE CONSTRAINT fk_<table>_tenant;

B. NOT NULL 表（6 张，禁止 SET NULL，否则 VALIDATE 永远失败）：
   unified_templates / notification_groups / notification_recipients /
   notification_deliveries / channel_strategies / recipient_rules
   1) 先导出孤儿清单人工确认；
   2) 按业务重映射到有效租户，或 DELETE 后重建；
   3) 再 ALTER TABLE <table> VALIDATE CONSTRAINT fk_<table>_tenant。

downgrade 删除外键并恢复两张审计表的 NOT NULL（存在 NULL 行时需先清理）。
"""
import sqlalchemy as sa
from alembic import op

revision = "p3a6_tenant_fk"
down_revision = "p3a5_usage_daily_unique"
branch_labels = None
depends_on = None

FK_TABLES = (
    "email_templates",
    "message_templates",
    "notification_logs",
    "notification_preferences",
    "rule_set_audit_logs",
    "schedule_audit_logs",
    "unified_templates",
    "notification_groups",
    "notification_recipients",
    "notification_deliveries",
    "channel_strategies",
    "recipient_rules",
    "news",
    "notices",
    "banners",
    "content_versions",
)


def upgrade() -> None:
    op.alter_column("rule_set_audit_logs", "tenant_id", nullable=True)
    op.alter_column("schedule_audit_logs", "tenant_id", nullable=True)

    for table_name in FK_TABLES:
        op.create_foreign_key(
            f"fk_{table_name}_tenant",
            table_name,
            "tenants",
            ["tenant_id"],
            ["id"],
            postgresql_not_valid=True,
        )


def downgrade() -> None:
    for table_name in FK_TABLES:
        op.drop_constraint(f"fk_{table_name}_tenant", table_name, type_="foreignkey")

    op.alter_column("schedule_audit_logs", "tenant_id", nullable=False)
    op.alter_column("rule_set_audit_logs", "tenant_id", nullable=False)
