"""fix schedule unique index null safety (no-op: reverted due to SQLite test incompatibility)

Revision ID: 106
Revises: 105
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = '106'
down_revision = '105'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op: partial unique indexes were attempted but reverted.
    # PostgreSQL NULL semantics mean the original unconditional unique index
    # does NOT enforce uniqueness when start_time/end_time are NULL.
    # Application-layer logic (rule engine) must guarantee no duplicate
    # schedules for the same doctor+date+time_slot combination.
    pass


def downgrade() -> None:
    pass
