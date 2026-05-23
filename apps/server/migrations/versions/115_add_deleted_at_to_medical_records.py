"""add deleted_at to medical_records for soft delete

Revision ID: 115
Revises: 114
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '115'
down_revision = '114'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('medical_records', sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='软删除时间'))
    op.create_index('ix_medical_records_deleted_at', 'medical_records', ['deleted_at'])


def downgrade() -> None:
    op.drop_index('ix_medical_records_deleted_at', table_name='medical_records')
    op.drop_column('medical_records', 'deleted_at')
