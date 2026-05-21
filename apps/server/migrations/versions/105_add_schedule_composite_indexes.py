"""add composite indexes to schedules

Revision ID: 105
Revises: 104
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = '105'
down_revision = '104'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('ix_schedules_store_date', 'schedules', ['store_id', 'schedule_date'])
    op.create_index('ix_schedules_doctor_date', 'schedules', ['doctor_id', 'schedule_date'])
    op.create_index('ix_schedules_tenant_store_date', 'schedules', ['tenant_id', 'store_id', 'schedule_date'])


def downgrade() -> None:
    op.drop_index('ix_schedules_tenant_store_date', table_name='schedules')
    op.drop_index('ix_schedules_doctor_date', table_name='schedules')
    op.drop_index('ix_schedules_store_date', table_name='schedules')
