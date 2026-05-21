"""Add tenant_id to doctor_booking_settings

Revision ID: 087_add_tenant_id_to_doctor_booking_settings
Revises: 086
Create Date: 2026-05-20

"""
from alembic import op
import sqlalchemy as sa


revision = '087_add_tenant_id_to_doctor_booking_settings'
down_revision = '086_seed_default_email_templates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'doctor_booking_settings',
        sa.Column('tenant_id', sa.String(36), nullable=True, comment='租户ID'),
    )
    op.create_index(
        'ix_doctor_booking_settings_tenant_id',
        'doctor_booking_settings',
        ['tenant_id'],
    )
    op.create_foreign_key(
        'fk_doctor_booking_settings_tenant_id',
        'doctor_booking_settings',
        'tenants',
        ['tenant_id'],
        ['id'],
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_doctor_booking_settings_tenant_id',
        'doctor_booking_settings',
        type_='foreignkey',
    )
    op.drop_index(
        'ix_doctor_booking_settings_tenant_id',
        'doctor_booking_settings',
    )
    op.drop_column('doctor_booking_settings', 'tenant_id')
