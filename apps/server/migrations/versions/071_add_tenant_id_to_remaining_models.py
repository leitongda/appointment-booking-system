"""为多个业务表添加 tenant_id 字段

Revision ID: 071_add_tenant_id_to_remaining_models
Revises: 070
Create Date: 2026-04-28

"""
from alembic import op
import sqlalchemy as sa


revision = '071_add_tenant_id_to_remaining_models'
down_revision = '070_add_tenant_audit_log'
branch_labels = None
depends_on = None


def upgrade():
    # point_logs
    op.add_column('point_logs', sa.Column('tenant_id', sa.String(36), nullable=True, comment='租户ID'))
    op.create_index('ix_point_logs_tenant_id', 'point_logs', ['tenant_id'])
    op.create_foreign_key('fk_point_logs_tenant_id', 'point_logs', 'tenants', ['tenant_id'], ['id'])

    # waitlist_entries
    op.add_column('waitlist_entries', sa.Column('tenant_id', sa.String(36), nullable=True, comment='租户ID'))
    op.create_index('ix_waitlist_entries_tenant_id', 'waitlist_entries', ['tenant_id'])
    op.create_foreign_key('fk_waitlist_entries_tenant_id', 'waitlist_entries', 'tenants', ['tenant_id'], ['id'])

    # user_favorites
    op.add_column('user_favorites', sa.Column('tenant_id', sa.String(36), nullable=True, comment='租户ID'))
    op.create_index('ix_user_favorites_tenant_id', 'user_favorites', ['tenant_id'])
    op.create_foreign_key('fk_user_favorites_tenant_id', 'user_favorites', 'tenants', ['tenant_id'], ['id'])

    # booking_notices
    op.add_column('booking_notices', sa.Column('tenant_id', sa.String(36), nullable=True, comment='租户ID'))
    op.create_index('ix_booking_notices_tenant_id', 'booking_notices', ['tenant_id'])
    op.create_foreign_key('fk_booking_notices_tenant_id', 'booking_notices', 'tenants', ['tenant_id'], ['id'])

    # user_behavior_logs
    op.add_column('user_behavior_logs', sa.Column('tenant_id', sa.String(36), nullable=True, comment='租户ID'))
    op.create_index('ix_user_behavior_logs_tenant_id', 'user_behavior_logs', ['tenant_id'])
    op.create_foreign_key('fk_user_behavior_logs_tenant_id', 'user_behavior_logs', 'tenants', ['tenant_id'], ['id'])


def downgrade():
    # user_behavior_logs
    op.drop_constraint('fk_user_behavior_logs_tenant_id', 'user_behavior_logs', type_='foreignkey')
    op.drop_index('ix_user_behavior_logs_tenant_id', 'user_behavior_logs')
    op.drop_column('user_behavior_logs', 'tenant_id')

    # booking_notices
    op.drop_constraint('fk_booking_notices_tenant_id', 'booking_notices', type_='foreignkey')
    op.drop_index('ix_booking_notices_tenant_id', 'booking_notices')
    op.drop_column('booking_notices', 'tenant_id')

    # user_favorites
    op.drop_constraint('fk_user_favorites_tenant_id', 'user_favorites', type_='foreignkey')
    op.drop_index('ix_user_favorites_tenant_id', 'user_favorites')
    op.drop_column('user_favorites', 'tenant_id')

    # waitlist_entries
    op.drop_constraint('fk_waitlist_entries_tenant_id', 'waitlist_entries', type_='foreignkey')
    op.drop_index('ix_waitlist_entries_tenant_id', 'waitlist_entries')
    op.drop_column('waitlist_entries', 'tenant_id')

    # point_logs
    op.drop_constraint('fk_point_logs_tenant_id', 'point_logs', type_='foreignkey')
    op.drop_index('ix_point_logs_tenant_id', 'point_logs')
    op.drop_column('point_logs', 'tenant_id')
