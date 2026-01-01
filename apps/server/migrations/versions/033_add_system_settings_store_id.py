"""add store_id to system_settings

Revision ID: 033_store_settings
Revises: 032_add_break_times
Create Date: 2026-01-01

为 system_settings 表添加 store_id 字段，支持门店级别配置
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '033_store_settings'
down_revision = '032_add_break_times'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加 store_id 列
    op.add_column('system_settings', sa.Column('store_id', sa.String(36), nullable=True))
    
    # 添加外键约束
    op.create_foreign_key(
        'fk_system_settings_store_id',
        'system_settings',
        'stores',
        ['store_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # 添加索引：加速按门店和分类查询
    op.create_index(
        'ix_system_settings_store_category',
        'system_settings',
        ['store_id', 'category']
    )
    op.create_index(
        'ix_system_settings_store_category_key',
        'system_settings',
        ['store_id', 'category', 'key']
    )


def downgrade() -> None:
    # 删除索引
    op.drop_index('ix_system_settings_store_category_key', table_name='system_settings')
    op.drop_index('ix_system_settings_store_category', table_name='system_settings')
    
    # 删除外键约束
    op.drop_constraint('fk_system_settings_store_id', 'system_settings', type_='foreignkey')
    
    # 删除列
    op.drop_column('system_settings', 'store_id')

