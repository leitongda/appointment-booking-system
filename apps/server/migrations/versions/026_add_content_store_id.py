"""为内容管理相关表添加 store_id 字段

Revision ID: 026_add_content_store_id
Revises: 025_add_store_wechat_config
Create Date: 2024-12-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '026_add_content_store_id'
down_revision = '025_add_store_wechat_config'
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


def upgrade():
    """为内容管理相关表添加 store_id 字段"""
    
    # 需要添加 store_id 的表列表
    tables_to_update = [
        ('news', 'idx_news_store_id'),
        ('notices', 'idx_notices_store_id'),
        ('banners', 'idx_banners_store_id'),
        ('messages', 'idx_messages_store_id'),
    ]
    
    for table_name, index_name in tables_to_update:
        if not table_exists(table_name):
            print(f"表 {table_name} 不存在，跳过")
            continue
            
        if column_exists(table_name, 'store_id'):
            print(f"表 {table_name} 已存在 store_id 字段，跳过")
        else:
            # 添加 store_id 列
            op.add_column(
                table_name,
                sa.Column(
                    'store_id',
                    sa.String(36),
                    sa.ForeignKey('stores.id', ondelete='SET NULL'),
                    nullable=True,
                    index=True,
                    comment='所属门店ID，NULL表示全局'
                )
            )
            print(f"表 {table_name} 已添加 store_id 字段")
            
            # 创建索引（如果不存在）
            if not index_exists(table_name, index_name):
                try:
                    op.create_index(index_name, table_name, ['store_id'])
                    print(f"已创建索引 {index_name}")
                except Exception as e:
                    print(f"创建索引 {index_name} 失败: {e}")
    
    # 单独处理 patients 表（使用不同的注释）
    if table_exists('patients'):
        if column_exists('patients', 'store_id'):
            print("表 patients 已存在 store_id 字段，跳过")
        else:
            op.add_column(
                'patients',
                sa.Column(
                    'store_id',
                    sa.String(36),
                    sa.ForeignKey('stores.id', ondelete='SET NULL'),
                    nullable=True,
                    index=True,
                    comment='首次就诊门店ID'
                )
            )
            print("表 patients 已添加 store_id 字段")
            
            if not index_exists('patients', 'idx_patients_store_id'):
                try:
                    op.create_index('idx_patients_store_id', 'patients', ['store_id'])
                    print("已创建索引 idx_patients_store_id")
                except Exception as e:
                    print(f"创建索引 idx_patients_store_id 失败: {e}")


def downgrade():
    """删除 store_id 字段"""
    
    tables_to_update = [
        ('news', 'idx_news_store_id'),
        ('notices', 'idx_notices_store_id'),
        ('banners', 'idx_banners_store_id'),
        ('messages', 'idx_messages_store_id'),
        ('patients', 'idx_patients_store_id'),
    ]
    
    for table_name, index_name in tables_to_update:
        if not table_exists(table_name):
            continue
            
        if column_exists(table_name, 'store_id'):
            # 先删除索引
            if index_exists(table_name, index_name):
                try:
                    op.drop_index(index_name, table_name)
                except Exception:
                    pass
            
            # 删除列
            op.drop_column(table_name, 'store_id')
            print(f"表 {table_name} 已删除 store_id 字段")

