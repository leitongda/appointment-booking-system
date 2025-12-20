"""Multi-tenant architecture migration

Revision ID: 016_multi_tenant
Revises: 015_add_user_behavior_logs
Create Date: 2024-12-19 10:00:00.000000

Multi-tenant architecture changes:
1. Add store_id to admins table
2. Drop store_departments table (switching to direct Department.store_id)
3. Make Department.store_id non-nullable (after data migration)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision = '016_multi_tenant'
down_revision = '015_add_user_behavior_logs'
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    bind = op.get_bind()
    
    # 1. Admin 表添加 store_id 字段
    if table_exists('admins') and not column_exists('admins', 'store_id'):
        op.add_column('admins', sa.Column(
            'store_id', 
            sa.String(36), 
            sa.ForeignKey('stores.id', ondelete='SET NULL'),
            nullable=True, 
            comment='所属门店ID，超级管理员为空'
        ))
        # 创建索引
        op.create_index('idx_admins_store_id', 'admins', ['store_id'])
    
    # 2. 处理 departments 表中 store_id 为空的数据
    # 先获取第一个门店作为默认门店
    if table_exists('departments') and table_exists('stores'):
        result = bind.execute(text("SELECT id FROM stores LIMIT 1"))
        first_store = result.fetchone()
        
        if first_store:
            default_store_id = first_store[0]
            # 将 store_id 为空的科室分配到默认门店
            bind.execute(text(
                f"UPDATE departments SET store_id = :store_id WHERE store_id IS NULL"
            ), {"store_id": default_store_id})
    
    # 3. 删除 store_departments 关联表（科室改为门店独有模式）
    if table_exists('store_departments'):
        op.drop_table('store_departments')
    
    # 4. 将 Department.store_id 改为必填（如果还有空值则跳过）
    # 注意：这一步需要确保数据已迁移完成
    # 由于 SQLite 不支持 ALTER COLUMN，这里跳过 nullable 修改
    # 在 MySQL/PostgreSQL 环境下可以启用以下代码：
    # if table_exists('departments'):
    #     try:
    #         op.alter_column('departments', 'store_id', nullable=False)
    #     except Exception as e:
    #         print(f"Warning: Could not alter column nullable: {e}")


def downgrade() -> None:
    bind = op.get_bind()
    
    # 1. 删除 admins.store_id 字段
    if table_exists('admins') and column_exists('admins', 'store_id'):
        try:
            op.drop_index('idx_admins_store_id', 'admins')
        except:
            pass
        op.drop_column('admins', 'store_id')
    
    # 2. 重新创建 store_departments 关联表
    if not table_exists('store_departments'):
        op.create_table(
            'store_departments',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=False, comment='门店ID'),
            sa.Column('department_id', sa.String(36), sa.ForeignKey('departments.id'), nullable=False, comment='科室ID'),
            sa.Column('floor', sa.String(20), nullable=True, comment='楼层'),
            sa.Column('room', sa.String(50), nullable=True, comment='诊室'),
            sa.Column('status', sa.Integer, default=1, comment='状态: 0-停诊 1-正常'),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        )
    
    # 3. Department.store_id 恢复为可空
    # if table_exists('departments'):
    #     try:
    #         op.alter_column('departments', 'store_id', nullable=True)
    #     except Exception as e:
    #         print(f"Warning: Could not alter column nullable: {e}")

