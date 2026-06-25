"""merge session_events and store_lat_lng_fix

Revision ID: 520ef7fe0ba7
Revises: 123, b4102284e62c
Create Date: 2026-06-18 14:07:04.550288

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '520ef7fe0ba7'
down_revision = ('123', 'b4102284e62c')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

