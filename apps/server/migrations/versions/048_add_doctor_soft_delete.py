"""add deleted_at column to doctors table

Revision ID: 048_doctor_soft_delete
Revises: 047_add_rule_window_name
Create Date: 2026-03-29

为 doctors 表添加 deleted_at 字段，支持软删除。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '048_doctor_soft_delete'
down_revision = '047_add_rule_window_name'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('doctors', sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='软删除时间'))


def downgrade() -> None:
    op.drop_column('doctors', 'deleted_at')
