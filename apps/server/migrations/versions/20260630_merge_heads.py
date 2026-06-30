"""合并迁移头

合并 20260630_add_encrypted 和 96a47e60a416 两个迁移头。

Revision ID: 20260630_merge_heads
Revises: 20260630_add_encrypted, 96a47e60a416
Create Date: 2026-06-30
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260630_merge_heads'
down_revision = ('20260630_add_encrypted', '96a47e60a416')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 合并迁移，无实际操作
    pass


def downgrade() -> None:
    # 合并迁移，无实际操作
    pass
