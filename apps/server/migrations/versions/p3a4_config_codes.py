"""P3-4: config codes become tenant-scoped unique

Revision ID: p3a4_config_codes
Revises: p3a3_business_numbers
Create Date: 2026-10-23

shift_types.code / message_templates.code / guide_tours.code 改为 (tenant_id, code) 唯一，
平台行（tenant_id IS NULL）用 partial unique index 保持唯一。
三列原均为全局唯一，存量 shift_types 全部为平台级（tenant_id=NULL），不回填。
downgrade 恢复全局唯一；跨租户同 code 存在时会失败。
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


def upgrade() -> None:
    for table, column, old_constraint, uq_name, idx_name in TARGETS:
        op.drop_constraint(old_constraint, table, type_="unique")
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
