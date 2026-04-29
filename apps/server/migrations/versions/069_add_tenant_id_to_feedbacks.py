"""反馈表添加 tenant_id 字段

Revision ID: 069_add_tenant_id_to_feedbacks
Revises: 068
Create Date: 2026-04-28

"""
from alembic import op
import sqlalchemy as sa


revision = '069_add_tenant_id_to_feedbacks'
down_revision = '068_add_tenant_id_to_operation_logs'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('feedbacks', sa.Column('tenant_id', sa.String(36), nullable=True, comment='租户ID'))
    op.create_index('ix_feedbacks_tenant_id', 'feedbacks', ['tenant_id'])
    op.create_foreign_key('fk_feedbacks_tenant_id', 'feedbacks', 'tenants', ['tenant_id'], ['id'])

    # 回填：通过 user_id 关联 users 表获取 tenant_id
    op.execute("""
        UPDATE feedbacks f
        SET tenant_id = u.tenant_id
        FROM users u
        WHERE f.user_id = u.id AND u.tenant_id IS NOT NULL
    """)


def downgrade():
    op.drop_constraint('fk_feedbacks_tenant_id', 'feedbacks', type_='foreignkey')
    op.drop_index('ix_feedbacks_tenant_id', 'feedbacks')
    op.drop_column('feedbacks', 'tenant_id')
