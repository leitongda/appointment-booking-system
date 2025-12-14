"""add new fields to stores table

Revision ID: 003
Revises: 002_add_doctor_fields
Create Date: 2024-01-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003_add_store_fields'
down_revision = '002_add_doctor_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加门店密码字段
    op.add_column('stores', sa.Column('password', sa.String(100), nullable=True, comment='门店密码'))
    
    # 添加邮箱字段
    op.add_column('stores', sa.Column('email', sa.String(100), nullable=True, comment='邮箱'))
    
    # 添加门店logo字段
    op.add_column('stores', sa.Column('logo', sa.String(255), nullable=True, comment='门店logo'))
    
    # 添加风格选择字段
    op.add_column('stores', sa.Column('theme_style', sa.String(50), nullable=True, comment='风格选择'))


def downgrade() -> None:
    # 删除风格选择字段
    op.drop_column('stores', 'theme_style')
    
    # 删除门店logo字段
    op.drop_column('stores', 'logo')
    
    # 删除邮箱字段
    op.drop_column('stores', 'email')
    
    # 删除门店密码字段
    op.drop_column('stores', 'password')
