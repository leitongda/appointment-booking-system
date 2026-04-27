"""add store_id and department_id to rule_sets

Revision ID: 062
Revises: 061
Create Date: 2026-04-27 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '062'
down_revision: Union[str, None] = '061'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add store_id and department_id columns to rule_sets table."""
    # 添加门店ID列（可为空，表示租户级）
    op.add_column(
        'rule_sets',
        sa.Column(
            'store_id',
            sa.String(36),
            nullable=True,
            comment='门店ID（可选，为空表示租户级）'
        )
    )

    # 添加科室ID列（可为空，表示门店级）
    op.add_column(
        'rule_sets',
        sa.Column(
            'department_id',
            sa.String(36),
            nullable=True,
            comment='科室ID（可选，为空表示门店级）'
        )
    )

    # 创建索引以提高查询性能
    op.create_index(
        'idx_rule_sets_store_id',
        'rule_sets',
        ['store_id']
    )

    op.create_index(
        'idx_rule_sets_department_id',
        'rule_sets',
        ['department_id']
    )

    # 添加外键约束
    op.create_foreign_key(
        'fk_rule_sets_store_id',
        'rule_sets',
        'stores',
        ['store_id'],
        ['id']
    )

    op.create_foreign_key(
        'fk_rule_sets_department_id',
        'rule_sets',
        'departments',
        ['department_id'],
        ['id']
    )


def downgrade() -> None:
    """Remove store_id and department_id columns from rule_sets table."""
    # 删除外键约束
    op.drop_constraint('fk_rule_sets_department_id', 'rule_sets', type_='foreignkey')
    op.drop_constraint('fk_rule_sets_store_id', 'rule_sets', type_='foreignkey')

    # 删除索引
    op.drop_index('idx_rule_sets_department_id', table_name='rule_sets')
    op.drop_index('idx_rule_sets_store_id', table_name='rule_sets')

    # 删除列
    op.drop_column('rule_sets', 'department_id')
    op.drop_column('rule_sets', 'store_id')
