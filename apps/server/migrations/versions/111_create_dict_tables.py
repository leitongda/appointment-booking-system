"""create dict_types and dict_items tables

Revision ID: 111
Revises: 110
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa

revision = '111'
down_revision = '110'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 创建 dict_types 表
    op.create_table(
        'dict_types',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('code', sa.String(50), nullable=False, comment='字典类型编码'),
        sa.Column('name', sa.String(100), nullable=False, comment='字典类型名称'),
        sa.Column('description', sa.Text, nullable=True, comment='描述'),
        sa.Column('status', sa.Integer, nullable=False, server_default='1', comment='状态 1=启用 0=禁用'),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True, comment='租户ID'),
        sa.Column('created_at', sa.DateTime, nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime, nullable=True, comment='更新时间'),
        sa.Column('created_by', sa.String(36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(36), nullable=True, comment='更新人ID'),
        sa.UniqueConstraint('code', 'tenant_id', name='uq_dict_type_code_tenant'),
        comment='字典类型表',
    )

    # 2. 创建 dict_items 表
    op.create_table(
        'dict_items',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('dict_type_id', sa.String(36), sa.ForeignKey('dict_types.id', ondelete='CASCADE'), nullable=False, index=True, comment='字典类型ID'),
        sa.Column('label', sa.String(200), nullable=False, comment='显示标签'),
        sa.Column('value', sa.String(100), nullable=False, comment='字典值'),
        sa.Column('sort_order', sa.Integer, nullable=False, server_default='0', comment='排序'),
        sa.Column('status', sa.Integer, nullable=False, server_default='1', comment='状态 1=启用 0=禁用'),
        sa.Column('extra', sa.JSON, nullable=True, comment='扩展数据'),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True, comment='租户ID'),
        sa.Column('created_at', sa.DateTime, nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime, nullable=True, comment='更新时间'),
        sa.Column('created_by', sa.String(36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(36), nullable=True, comment='更新人ID'),
        sa.UniqueConstraint('dict_type_id', 'value', 'tenant_id', name='uq_dict_item_value_tenant'),
        comment='字典项表',
    )


def downgrade() -> None:
    op.drop_table('dict_items')
    op.drop_table('dict_types')
