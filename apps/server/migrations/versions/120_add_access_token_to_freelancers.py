"""add access_token to freelance_freelancers

Revision ID: 120
Revises: 119
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa


revision = '120'
down_revision = '119'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    if not column_exists('freelance_freelancers', 'access_token'):
        op.add_column('freelance_freelancers', sa.Column('access_token', sa.String(64), nullable=True, unique=True, index=True))
    # Backfill existing records
    op.execute("""
        UPDATE freelance_freelancers
        SET access_token = md5(random()::text || id::text)
        WHERE access_token IS NULL
    """)


def downgrade() -> None:
    op.drop_column('freelance_freelancers', 'access_token')
