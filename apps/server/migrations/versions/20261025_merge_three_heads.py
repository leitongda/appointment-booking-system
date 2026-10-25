"""Merge heads: p3a8 + main 既有两链（917769a35fcb / 061_add_soft_delete_to_rule_sets）

feat/tenant-isolation-hardening 合入 main 后出现三个头：
- p3a8_fee_tenant（租户链延续）
- 917769a35fcb（main 上 p3a7 × TCM 127 链的合并点）
- 061_add_soft_delete_to_rule_sets（TCM 编号链的另一支尽头）

本迁移仅合头，无实际 DDL。
"""
from alembic import op

revision = "20261025_merge_three_heads"
down_revision = ("917769a35fcb", "061_add_soft_delete_to_rule_sets", "p3a8_fee_tenant")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
