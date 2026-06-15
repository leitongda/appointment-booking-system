"""add edges column to approval_flow_definitions

Revision ID: 349003eaa3ce
Revises: bbd1837de5ec
Create Date: 2026-06-08 09:26:29.973485

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '349003eaa3ce'
down_revision = 'bbd1837de5ec'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Only add edges column to approval_flow_definitions
    op.add_column('approval_flow_definitions', sa.Column('edges', sa.JSON(), nullable=True, comment='流程连线 [{source, target, sourceHandle, targetHandle}]'))


def downgrade() -> None:
    op.drop_column('approval_flow_definitions', 'edges')

