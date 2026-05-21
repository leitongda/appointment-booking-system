"""Backfill quota fields from existing total_slots

Revision ID: 093_backfill_quota_fields
Revises: 092_add_quota_fields_to_schedules
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa

revision = '093_backfill_quota_fields'
down_revision = '092_add_quota_fields_to_schedules'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 将现有 total_slots 回填到 online_quota（线上号源 = 原有全部号源）
    op.execute(
        "UPDATE schedules SET online_quota = total_slots WHERE online_quota = 0"
    )


def downgrade() -> None:
    # 回滚：将 online_quota 清零（total_slots 保持不变）
    op.execute("UPDATE schedules SET online_quota = 0")
