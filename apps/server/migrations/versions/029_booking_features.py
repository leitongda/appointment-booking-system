"""add booking features (symptom_description, booking_notices, user_favorites)

Revision ID: 029_booking_features
Revises: 028_wechat_fields
Create Date: 2024-12-31

Add symptom_description to appointments table
Create booking_notices table
Create user_favorites table
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '029_booking_features'
down_revision = '028_wechat_fields'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    try:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except:
        return False


def table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # 1. 添加 symptom_description 到 appointments 表
    if not column_exists('appointments', 'symptom_description'):
        op.add_column('appointments', sa.Column(
            'symptom_description', 
            sa.Text, 
            nullable=True, 
            comment='病情描述/预填信息'
        ))
    
    # 2. 创建 booking_notices 表
    if not table_exists('booking_notices'):
        op.create_table(
            'booking_notices',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('type', sa.String(50), nullable=False, comment='类型: BOOKING/VISIT/REFUND'),
            sa.Column('title', sa.String(100), nullable=True, comment='标题'),
            sa.Column('content', sa.Text, nullable=True, comment='内容'),
            sa.Column('sort_order', sa.Integer, server_default='0', comment='排序'),
            sa.Column('status', sa.Integer, server_default='1', comment='状态: 0禁用 1启用'),
            # 审计字段
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.Column('created_by', sa.String(36), nullable=True),
            sa.Column('updated_by', sa.String(36), nullable=True),
        )
        # 创建索引
        op.create_index('ix_booking_notices_type', 'booking_notices', ['type'])
        op.create_index('ix_booking_notices_status', 'booking_notices', ['status'])
    
    # 3. 创建 user_favorites 表
    if not table_exists('user_favorites'):
        op.create_table(
            'user_favorites',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False, comment='用户ID'),
            sa.Column('target_type', sa.String(20), nullable=False, comment='收藏类型: doctor/department'),
            sa.Column('target_id', sa.String(36), nullable=False, comment='收藏目标ID'),
            # 审计字段
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.Column('created_by', sa.String(36), nullable=True),
            sa.Column('updated_by', sa.String(36), nullable=True),
        )
        # 创建索引
        op.create_index('ix_user_favorites_user_id', 'user_favorites', ['user_id'])
        op.create_index('ix_user_favorites_target', 'user_favorites', ['target_type', 'target_id'])
        # 创建联合唯一约束
        op.create_unique_constraint('uq_user_favorite', 'user_favorites', ['user_id', 'target_type', 'target_id'])


def downgrade() -> None:
    # 删除 user_favorites 表
    if table_exists('user_favorites'):
        op.drop_table('user_favorites')
    
    # 删除 booking_notices 表
    if table_exists('booking_notices'):
        op.drop_table('booking_notices')
    
    # 删除 symptom_description 列
    if column_exists('appointments', 'symptom_description'):
        op.drop_column('appointments', 'symptom_description')

