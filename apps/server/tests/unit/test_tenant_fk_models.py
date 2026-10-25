"""R3-8：M6 的 16 张表在模型层必须声明 tenant_id -> tenants.id 外键。

本用例不连数据库，只检查 SQLAlchemy 元数据，用于锁住 p3a6 已建外键与
模型声明的一致性，避免 `alembic autogenerate` 把遗漏的外键识别为 diff。
"""
import pytest

import app.models  # noqa: F401  确保全部模型注册到 Base.metadata
from app.db.base import Base

# p3a6_tenant_fk.py 的 FK_TABLES 全量
M6_TABLES = (
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

# R3-8 本次补外键的 7 个模型列
NEWLY_DECLARED_FK_TABLES = (
    "unified_templates",
    "notification_groups",
    "notification_recipients",
    "notification_deliveries",
    "channel_strategies",
    "recipient_rules",
    "content_versions",
)


# p3a8_fee_tenant.py 的 TABLES 全量（诊费 + 门店邮件接收人，2026-10-24 新增）
P3A8_TABLES = (
    "consultation_fee_types",
    "consultation_fee_templates",
    "store_fee_templates",
    "doctor_consultation_fees",
    "store_email_recipients",
)


@pytest.mark.parametrize("table_name", M6_TABLES)
def test_m6_table_declares_tenant_fk(table_name: str) -> None:
    """每张 M6 表的 tenant_id 都必须指向 tenants.id。"""
    table = Base.metadata.tables.get(table_name)
    assert table is not None, f"模型未注册表 {table_name}"
    column = table.columns.get("tenant_id")
    assert column is not None, f"{table_name} 缺少 tenant_id 列"
    targets = {fk.target_fullname for fk in column.foreign_keys}
    assert targets == {"tenants.id"}, f"{table_name}.tenant_id 外键指向为 {targets}"


@pytest.mark.parametrize("table_name", P3A8_TABLES)
def test_p3a8_table_declares_tenant_fk(table_name: str) -> None:
    """p3a8 的 5 张表模型层必须声明 tenant_id -> tenants.id 外键。"""
    table = Base.metadata.tables.get(table_name)
    assert table is not None, f"模型未注册表 {table_name}"
    column = table.columns.get("tenant_id")
    assert column is not None, f"{table_name} 缺少 tenant_id 列"
    targets = {fk.target_fullname for fk in column.foreign_keys}
    assert targets == {"tenants.id"}, f"{table_name}.tenant_id 外键指向为 {targets}"
    assert column.nullable, f"{table_name}.tenant_id 应可空（存量回填前不做 NOT NULL）"


def test_newly_declared_fk_tables_are_covered() -> None:
    """R3-8 的 7 个模型列都在 M6 表清单内，防止清单漏项。"""
    assert len(NEWLY_DECLARED_FK_TABLES) == 7
    assert set(NEWLY_DECLARED_FK_TABLES) <= set(M6_TABLES)
