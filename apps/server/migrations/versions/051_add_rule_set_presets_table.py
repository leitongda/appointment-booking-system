"""Add rule_set_presets table

Revision ID: 051_add_rule_set_presets_table
Revises: 050_add_tenant_id_to_isolated_tables
Create Date: 2026-03-30

新增规则组预设模板表，支持系统预设和租户自定义预设。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '051_add_rule_set_presets_table'
down_revision = '050_add_tenant_id_to_isolated_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'rule_set_presets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True, comment='租户ID，null=全局系统预设'),
        sa.Column('name', sa.String(100), nullable=False, comment='预设名称'),
        sa.Column('description', sa.Text, nullable=True, comment='描述'),
        sa.Column('config', sa.JSON, nullable=False, comment='完整规则组配置'),
        sa.Column('is_system', sa.Boolean, nullable=False, server_default=sa.text('0'), comment='系统预设不可删除/修改'),
        sa.Column('sort_order', sa.Integer, nullable=False, server_default=sa.text('0'), comment='排序'),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('rule_set_presets')
