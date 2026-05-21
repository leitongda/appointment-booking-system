"""add rescheduled_from_id to appointments

Revision ID: 100
Revises: 099
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa

revision = '100'
down_revision = '099'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'appointments',
        sa.Column(
            'rescheduled_from_id',
            sa.String(36),
            nullable=True,
            index=True,
            comment='转约/改期来源预约ID',
        ),
    )


def downgrade() -> None:
    op.drop_index('ix_appointments_rescheduled_from_id', table_name='appointments')
    op.drop_column('appointments', 'rescheduled_from_id')
