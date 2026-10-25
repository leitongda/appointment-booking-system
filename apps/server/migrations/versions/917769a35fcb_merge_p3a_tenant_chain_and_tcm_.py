"""merge p3a tenant chain and tcm assistant_confirm_status

Revision ID: 917769a35fcb
Revises: p3a7_settings_tenant, 127_assistant_confirm_status
Create Date: 2026-10-25 12:32:48.091995

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '917769a35fcb'
down_revision = ('p3a7_settings_tenant', '127_assistant_confirm_status')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

