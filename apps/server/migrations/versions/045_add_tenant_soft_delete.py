"""add tenant soft delete columns

Revision ID: 045_add_tenant_soft_delete
Revises: 044_add_tenant_id_to_rule_tables
Create Date: 2026-03-27

为 tenants 表添加软删除字段 deleted_at 和 deleted_by
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '045_add_tenant_soft_delete'
down_revision = '044_add_tenant_id_to_rule_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tenants', sa.Column(
        'deleted_at', sa.DateTime,
        nullable=True,
        comment='软删除时间'
    ))
    op.add_column('tenants', sa.Column(
        'deleted_by', sa.String(36),
        nullable=True,
        comment='删除操作人ID'
    ))


def downgrade() -> None:
    op.drop_column('tenants', 'deleted_by')
    op.drop_column('tenants', 'deleted_at')
