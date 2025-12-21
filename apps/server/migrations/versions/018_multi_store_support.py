"""多门店支持：创建 admin_stores 关联表

Revision ID: 018_multi_store_support
Revises: 017_add_admin_login_history
Create Date: 2024-12-21

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '018_multi_store_support'
down_revision = '017_add_admin_login_history'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 创建 admin_stores 关联表（管理员-门店多对多关系）
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
    
    # 2. 将 admins.store_id 重命名为 current_store_id（当前选中门店）
    # 使用批处理模式以支持 SQLite
    with op.batch_alter_table('admins') as batch_op:
        batch_op.alter_column('store_id', new_column_name='current_store_id')
    
    # 3. 迁移现有数据：将 current_store_id 不为空的记录插入到 admin_stores
    # 使用原始 SQL 执行数据迁移
    connection = op.get_bind()
    connection.execute(sa.text("""
        INSERT INTO admin_stores (admin_id, store_id, is_manager, created_at)
        SELECT id, current_store_id, 1, datetime('now')
        FROM admins
        WHERE current_store_id IS NOT NULL
    """))


def downgrade() -> None:
    # 1. 将 current_store_id 重命名回 store_id
    with op.batch_alter_table('admins') as batch_op:
        batch_op.alter_column('current_store_id', new_column_name='store_id')
    
    # 2. 删除索引和表
    op.drop_index('ix_admin_stores_store_id', 'admin_stores')
    op.drop_index('ix_admin_stores_admin_id', 'admin_stores')
    op.drop_table('admin_stores')

