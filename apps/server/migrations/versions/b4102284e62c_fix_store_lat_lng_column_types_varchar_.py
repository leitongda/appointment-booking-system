"""fix store lat lng column types varchar to numeric

Revision ID: b4102284e62c
Revises: 122
Create Date: 2026-06-15 22:31:12.758127

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b4102284e62c'
down_revision = '122'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fix: stores.latitude/longitude were VARCHAR in DB but Numeric in ORM model,
    # causing "Unknown PG numeric type: 1043" with asyncpg.
    # PostgreSQL requires explicit USING clause for VARCHAR -> NUMERIC cast.
    op.execute("ALTER TABLE stores ALTER COLUMN latitude TYPE NUMERIC(10, 7) USING latitude::NUMERIC(10, 7)")
    op.execute("ALTER TABLE stores ALTER COLUMN longitude TYPE NUMERIC(10, 7) USING longitude::NUMERIC(10, 7)")


def downgrade() -> None:
    op.execute("ALTER TABLE stores ALTER COLUMN latitude TYPE VARCHAR(20) USING latitude::VARCHAR(20)")
    op.execute("ALTER TABLE stores ALTER COLUMN longitude TYPE VARCHAR(20) USING longitude::VARCHAR(20)")

