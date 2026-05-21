"""add department keywords for symptom matching

Revision ID: 099
Revises: 098
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa

revision = '099'
down_revision = '098'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('departments', sa.Column('keywords', sa.JSON(), nullable=True, comment='症状关键词JSON数组'))


def downgrade() -> None:
    op.drop_column('departments', 'keywords')
