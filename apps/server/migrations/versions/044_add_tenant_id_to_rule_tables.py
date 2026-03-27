"""add tenant_id to rule tables

Revision ID: 044_add_tenant_id_to_rule_tables
Revises: 043_tenant_id_not_null
Create Date: 2026-03-27

为规则管理相关表添加 tenant_id 字段，实现多租户隔离：
- shift_types: 班次类型表
- rule_sets: 规则组表
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '044_add_tenant_id_to_rule_tables'
down_revision = '043_tenant_id_not_null'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # shift_types 表添加 tenant_id
    op.add_column('shift_types', sa.Column(
        'tenant_id', sa.String(36),
        sa.ForeignKey('tenants.id'),
        nullable=True,
        comment='租户ID'
    ))
    op.create_index('idx_shift_types_tenant_id', 'shift_types', ['tenant_id'])

    # rule_sets 表添加 tenant_id
    op.add_column('rule_sets', sa.Column(
        'tenant_id', sa.String(36),
        sa.ForeignKey('tenants.id'),
        nullable=True,
        comment='租户ID'
    ))
    op.create_index('idx_rule_sets_tenant_id', 'rule_sets', ['tenant_id'])


def downgrade() -> None:
    # 删除 rule_sets 表的 tenant_id
    op.drop_index('idx_rule_sets_tenant_id', 'rule_sets')
    op.drop_column('rule_sets', 'tenant_id')

    # 删除 shift_types 表的 tenant_id
    op.drop_index('idx_shift_types_tenant_id', 'shift_types')
    op.drop_column('shift_types', 'tenant_id')
