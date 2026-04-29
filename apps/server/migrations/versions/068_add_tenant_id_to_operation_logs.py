"""操作日志表添加 tenant_id 字段

Revision ID: 068_add_tenant_id_to_operation_logs
Revises: 067
Create Date: 2026-04-28

"""
from alembic import op
import sqlalchemy as sa


revision = '068_add_tenant_id_to_operation_logs'
down_revision = '067_add_schedule_unique_constraint'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('operation_logs', sa.Column('tenant_id', sa.String(36), nullable=True, comment='租户ID'))
    op.create_index('ix_operation_logs_tenant_id', 'operation_logs', ['tenant_id'])
    op.create_foreign_key('fk_operation_logs_tenant_id', 'operation_logs', 'tenants', ['tenant_id'], ['id'])


def downgrade():
    op.drop_constraint('fk_operation_logs_tenant_id', 'operation_logs', type_='foreignkey')
    op.drop_index('ix_operation_logs_tenant_id', 'operation_logs')
    op.drop_column('operation_logs', 'tenant_id')
