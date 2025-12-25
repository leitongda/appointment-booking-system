"""添加门店诊费模板支持

Revision ID: 019_add_store_fee_templates
Revises: 018_multi_store_support
Create Date: 2024-12-25

1. 给 consultation_fee_types 表添加 store_id 列（允许门店自定义诊费类型）
2. 创建 store_fee_templates 表（门店诊费模板，可覆盖全局模板金额）
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '019_add_store_fee_templates'
down_revision = '018_multi_store_support'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    try:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def index_exists(table_name: str, index_name: str) -> bool:
    """检查索引是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    try:
        indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
        return index_name in indexes
    except Exception:
        return False


def upgrade() -> None:
    # 1. 给 consultation_fee_types 表添加 store_id 列
    # store_id = NULL 表示全局类型，store_id = 门店ID 表示门店专属类型
    if not column_exists('consultation_fee_types', 'store_id'):
        op.add_column(
            'consultation_fee_types',
            sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id', ondelete='CASCADE'), 
                      nullable=True, comment='门店ID，NULL表示全局类型')
        )
        # 创建索引
        op.create_index('ix_consultation_fee_types_store_id', 'consultation_fee_types', ['store_id'])
        
        # 修改 code 唯一索引为 (store_id, code) 复合唯一索引，允许不同门店有相同编码
        # 先删除原有的 code 唯一索引
        try:
            op.drop_index('ix_consultation_fee_types_code', 'consultation_fee_types')
        except Exception:
            pass
        # 创建复合唯一索引
        op.create_index(
            'ix_consultation_fee_types_store_code', 
            'consultation_fee_types', 
            ['store_id', 'code'], 
            unique=True
        )
    
    # 2. 创建门店诊费模板表
    if not table_exists('store_fee_templates'):
        op.create_table(
            'store_fee_templates',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id', ondelete='CASCADE'), 
                      nullable=False, comment='门店ID'),
            sa.Column('fee_type_id', sa.String(36), sa.ForeignKey('consultation_fee_types.id', ondelete='CASCADE'), 
                      nullable=False, comment='诊费类型ID'),
            sa.Column('initial_fee', sa.Numeric(10, 2), server_default='0', comment='初诊金额'),
            sa.Column('follow_up_fee', sa.Numeric(10, 2), server_default='0', comment='复诊金额'),
            sa.Column('status', sa.Integer, server_default='1', comment='状态: 0禁用 1启用'),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        # 创建索引
        op.create_index('ix_store_fee_templates_store_id', 'store_fee_templates', ['store_id'])
        op.create_index('ix_store_fee_templates_fee_type_id', 'store_fee_templates', ['fee_type_id'])
        # 复合唯一索引：同一门店的同一诊费类型只能有一条模板记录
        op.create_index(
            'ix_store_fee_templates_unique',
            'store_fee_templates',
            ['store_id', 'fee_type_id'],
            unique=True
        )


def downgrade() -> None:
    # 1. 删除门店诊费模板表
    if table_exists('store_fee_templates'):
        try:
            op.drop_index('ix_store_fee_templates_unique', 'store_fee_templates')
        except Exception:
            pass
        try:
            op.drop_index('ix_store_fee_templates_fee_type_id', 'store_fee_templates')
        except Exception:
            pass
        try:
            op.drop_index('ix_store_fee_templates_store_id', 'store_fee_templates')
        except Exception:
            pass
        op.drop_table('store_fee_templates')
    
    # 2. 删除 consultation_fee_types 表的 store_id 列
    if column_exists('consultation_fee_types', 'store_id'):
        # 恢复原有的 code 唯一索引
        try:
            op.drop_index('ix_consultation_fee_types_store_code', 'consultation_fee_types')
        except Exception:
            pass
        try:
            op.drop_index('ix_consultation_fee_types_store_id', 'consultation_fee_types')
        except Exception:
            pass
        op.create_index('ix_consultation_fee_types_code', 'consultation_fee_types', ['code'], unique=True)
        op.drop_column('consultation_fee_types', 'store_id')

