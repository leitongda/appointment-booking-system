"""添加权限表

Revision ID: 009
Revises: 008
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '009_add_permissions'
down_revision = '008_blacklist_and_booking_config'
branch_labels = None
depends_on = None


def upgrade():
    # 创建权限表
    op.create_table(
        'permissions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('code', sa.String(100), unique=True, nullable=False, comment='权限码'),
        sa.Column('name', sa.String(100), nullable=False, comment='权限名称'),
        sa.Column('type', sa.String(20), nullable=False, comment='类型: menu/button'),
        sa.Column('parent_code', sa.String(100), comment='父级权限码'),
        sa.Column('icon', sa.String(50), comment='图标'),
        sa.Column('sort', sa.Integer, default=0, comment='排序号'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.func.now()),
    )
    
    # 创建索引
    op.create_index('ix_permissions_code', 'permissions', ['code'])
    op.create_index('ix_permissions_parent_code', 'permissions', ['parent_code'])


def downgrade():
    op.drop_index('ix_permissions_parent_code', 'permissions')
    op.drop_index('ix_permissions_code', 'permissions')
    op.drop_table('permissions')

