"""Add quota fields and fee to schedules

Revision ID: 092_add_quota_fields_to_schedules
Revises: 091_backfill_schedule_publish_status
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa

revision = '092_add_quota_fields_to_schedules'
down_revision = '091_backfill_schedule_publish_status'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'schedules',
        sa.Column('online_quota', sa.Integer(), server_default='0', comment='线上号源'),
    )
    op.add_column(
        'schedules',
        sa.Column('offline_quota', sa.Integer(), server_default='0', comment='线下号源'),
    )
    op.add_column(
        'schedules',
        sa.Column('reserved_quota', sa.Integer(), server_default='0', comment='预留号源'),
    )
    op.add_column(
        'schedules',
        sa.Column('extra_quota', sa.Integer(), server_default='0', comment='加号号源'),
    )
    op.add_column(
        'schedules',
        sa.Column('fee', sa.Integer(), server_default='0', comment='挂号费(分)'),
    )


def downgrade() -> None:
    op.drop_column('schedules', 'fee')
    op.drop_column('schedules', 'extra_quota')
    op.drop_column('schedules', 'reserved_quota')
    op.drop_column('schedules', 'offline_quota')
    op.drop_column('schedules', 'online_quota')
