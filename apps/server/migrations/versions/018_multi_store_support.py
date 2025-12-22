"""多门店支持：创建 admin_stores 关联表

Revision ID: 018_multi_store_support
Revises: 017_add_admin_login_history
Create Date: 2024-12-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '018_multi_store_support'
down_revision = '017_add_admin_login_history'
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


def upgrade() -> None:
    # 1. 创建 admin_stores 关联表（管理员-门店多对多关系）
    if not table_exists('admin_stores'):
        op.create_table(
            'admin_stores',
            sa.Column('admin_id', sa.String(36), sa.ForeignKey('admins.id', ondelete='CASCADE'), primary_key=True, comment='管理员ID'),
            sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id', ondelete='CASCADE'), primary_key=True, comment='门店ID'),
            sa.Column('is_manager', sa.Integer, default=0, comment='是否为该门店管理员: 0否 1是'),
            sa.Column('created_at', sa.DateTime, default=datetime.utcnow, comment='创建时间'),
        )
        
        # 创建索引
        op.create_index('ix_admin_stores_admin_id', 'admin_stores', ['admin_id'])
        op.create_index('ix_admin_stores_store_id', 'admin_stores', ['store_id'])
    
    # 2. 处理 admins 表的 current_store_id 列
    has_store_id = column_exists('admins', 'store_id')
    has_current_store_id = column_exists('admins', 'current_store_id')
    
    if has_current_store_id:
        # current_store_id 已存在，跳过
        print("current_store_id already exists, skipping column operation")
    elif has_store_id:
        # 重命名 store_id -> current_store_id
        print("Renaming store_id to current_store_id")
        op.alter_column('admins', 'store_id', new_column_name='current_store_id')
        
        # 3. 迁移现有数据：将 current_store_id 不为空的记录插入到 admin_stores
        connection = op.get_bind()
        connection.execute(sa.text("""
            INSERT INTO admin_stores (admin_id, store_id, is_manager, created_at)
            SELECT id, current_store_id, 1, NOW()
            FROM admins
            WHERE current_store_id IS NOT NULL
            ON CONFLICT DO NOTHING
        """))
    else:
        # store_id 和 current_store_id 都不存在，直接创建 current_store_id
        print("Creating current_store_id column")
        op.add_column('admins', sa.Column(
            'current_store_id',
            sa.String(36),
            sa.ForeignKey('stores.id', ondelete='SET NULL'),
            nullable=True,
            comment='当前选中门店ID，超级管理员可为空'
        ))
        try:
            op.create_index('idx_admins_current_store_id', 'admins', ['current_store_id'])
        except Exception as e:
            print(f"Warning: Could not create index: {e}")


def downgrade() -> None:
    # 1. 将 current_store_id 重命名回 store_id
    if column_exists('admins', 'current_store_id'):
        try:
            op.drop_index('idx_admins_current_store_id', 'admins')
        except Exception:
            pass
        op.alter_column('admins', 'current_store_id', new_column_name='store_id')
    
    # 2. 删除索引和表
    if table_exists('admin_stores'):
        try:
            op.drop_index('ix_admin_stores_store_id', 'admin_stores')
        except Exception:
            pass
        try:
            op.drop_index('ix_admin_stores_admin_id', 'admin_stores')
        except Exception:
            pass
        op.drop_table('admin_stores')
