"""add doctor_id to rule_sets

Revision ID: 063
Revises: 062
Create Date: 2026-04-27 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '063'
down_revision: Union[str, None] = '062'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add doctor_id column to rule_sets table."""
    op.add_column(
        'rule_sets',
        sa.Column(
            'doctor_id',
            sa.String(36),
            nullable=True,
            comment='医生ID（可选，为空表示科室级）'
        )
    )

    op.create_index(
        'idx_rule_sets_doctor_id',
        'rule_sets',
        ['doctor_id']
    )

    op.create_foreign_key(
        'fk_rule_sets_doctor_id',
        'rule_sets',
        'doctors',
        ['doctor_id'],
        ['id']
    )


def downgrade() -> None:
    """Remove doctor_id column from rule_sets table."""
    op.drop_constraint('fk_rule_sets_doctor_id', 'rule_sets', type_='foreignkey')
    op.drop_index('idx_rule_sets_doctor_id', table_name='rule_sets')
    op.drop_column('rule_sets', 'doctor_id')
