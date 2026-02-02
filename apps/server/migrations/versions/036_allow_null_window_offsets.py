"""allow null window offsets

Revision ID: 036_null_offsets
Revises: 035_waitlist
Create Date: 2026-02-02

修改 rule_windows 表的 open_offset_sec 和 close_offset_sec 字段允许 NULL，
NULL 值表示"不限制"该边界。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '036_null_offsets'
down_revision = '035_add_waitlist'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 将 open_offset_sec 改为允许 NULL
    op.alter_column(
        'rule_windows',
        'open_offset_sec',
        existing_type=sa.Integer(),
        nullable=True,
        comment='开放偏移(秒),可负可正,NULL表示不限制'
    )

    # 将 close_offset_sec 改为允许 NULL
    op.alter_column(
        'rule_windows',
        'close_offset_sec',
        existing_type=sa.Integer(),
        nullable=True,
        comment='截止偏移(秒),可负可正,NULL表示不限制'
    )


def downgrade() -> None:
    # 回滚时需要先将 NULL 值更新为默认值，否则会失败
    # 将 NULL 的 open_offset_sec 更新为一个很大的负值（表示很早开放）
    op.execute("UPDATE rule_windows SET open_offset_sec = -31536000 WHERE open_offset_sec IS NULL")
    # 将 NULL 的 close_offset_sec 更新为一个很大的正值（表示永不截止）
    op.execute("UPDATE rule_windows SET close_offset_sec = 31536000 WHERE close_offset_sec IS NULL")

    # 将 open_offset_sec 改回不允许 NULL
    op.alter_column(
        'rule_windows',
        'open_offset_sec',
        existing_type=sa.Integer(),
        nullable=False,
        comment='开放偏移(秒),可负可正'
    )

    # 将 close_offset_sec 改回不允许 NULL
    op.alter_column(
        'rule_windows',
        'close_offset_sec',
        existing_type=sa.Integer(),
        nullable=False,
        comment='截止偏移(秒),可负可正'
    )
