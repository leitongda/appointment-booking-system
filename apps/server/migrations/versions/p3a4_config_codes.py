"""P3-4: config codes become tenant-scoped unique

Revision ID: p3a4_config_codes
Revises: p3a3_business_numbers
Create Date: 2026-10-23

shift_types.code / message_templates.code / guide_tours.code 改为 (tenant_id, code) 唯一，
平台行（tenant_id IS NULL）用 partial unique index 保持唯一。
三列原均为全局唯一，存量 shift_types 全部为平台级（tenant_id=NULL），不回填。
downgrade 恢复全局唯一；跨租户同 code 存在时会失败。

旧唯一性的形态兼容（2026-10-24 开发库演练发现）：
经 create_all 同步过的库（如开发库 guide_tours）旧唯一性可能是**唯一索引**
（ix_guide_tours_code）而非命名约束（guide_tours_code_key），直接
drop_constraint 会报 UndefinedObject。upgrade 按实际存在形态分别删除。
"""
import sqlalchemy as sa
from alembic import op

revision = "p3a4_config_codes"
down_revision = "p3a3_business_numbers"
branch_labels = None
depends_on = None

TARGETS = (
    ("shift_types", "code", "shift_types_code_key",
     "uq_shift_types_tenant_code", "uq_shift_types_code_platform"),
    ("message_templates", "code", "message_templates_code_key",
     "uq_message_templates_tenant_code", "uq_message_templates_code_platform"),
    ("guide_tours", "code", "guide_tours_code_key",
     "uq_guide_tours_tenant_code", "uq_guide_tours_code_platform"),
)


def _existing_single_column_unique(table: str, column: str):
    """找单列全局唯一性对象：优先唯一约束，其次唯一索引；无则 None。

    Returns:
        ("constraint", name) / ("index", name) / None
    """
    inspector = sa.inspect(op.get_bind())
    for constraint in inspector.get_unique_constraints(table):
        if (constraint.get("column_names") or []) == [column]:
            return ("constraint", constraint["name"])
    for index in inspector.get_indexes(table):
        if index.get("unique") and (index.get("column_names") or []) == [column]:
            return ("index", index["name"])
    return None


def upgrade() -> None:
    for table, column, old_constraint, uq_name, idx_name in TARGETS:
        existing = _existing_single_column_unique(table, column)
        if existing:
            kind, name = existing
            if kind == "constraint":
                op.drop_constraint(name, table, type_="unique")
            else:
                op.drop_index(name, table_name=table)
        op.create_unique_constraint(uq_name, table, ["tenant_id", column])
        op.create_index(
            idx_name,
            table,
            [column],
            unique=True,
            postgresql_where=sa.text("tenant_id IS NULL"),
        )


def downgrade() -> None:
    for table, column, old_constraint, uq_name, idx_name in TARGETS:
        op.drop_index(idx_name, table_name=table)
        op.drop_constraint(uq_name, table, type_="unique")
        op.create_unique_constraint(old_constraint, table, [column])
