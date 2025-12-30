"""add wechat fields to users

Revision ID: 028_wechat_fields
Revises: 027_patient_card_management
Create Date: 2024-12-30

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '028_wechat_fields'
down_revision = '027_patient_card_management'
branch_labels = None
depends_on = None


def upgrade():
    """添加微信相关字段到 users 表"""
    # 添加 unionid 字段
    op.add_column('users', sa.Column('unionid', sa.String(100), nullable=True, comment='微信开放平台统一ID'))
    op.create_index('ix_users_unionid', 'users', ['unionid'], unique=True)
    
    # 添加 wechat_nickname 字段
    op.add_column('users', sa.Column('wechat_nickname', sa.String(50), nullable=True, comment='微信原始昵称'))
    
    # 添加 wechat_avatar 字段
    op.add_column('users', sa.Column('wechat_avatar', sa.String(500), nullable=True, comment='微信原始头像URL'))
    
    # 添加 wechat_synced_at 字段
    op.add_column('users', sa.Column('wechat_synced_at', sa.DateTime(), nullable=True, comment='最后同步微信信息时间'))


def downgrade():
    """回滚：删除微信相关字段"""
    op.drop_index('ix_users_unionid', table_name='users')
    op.drop_column('users', 'wechat_synced_at')
    op.drop_column('users', 'wechat_avatar')
    op.drop_column('users', 'wechat_nickname')
    op.drop_column('users', 'unionid')

