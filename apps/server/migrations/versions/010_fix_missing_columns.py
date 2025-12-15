"""fix missing columns in stores, departments, doctors tables

Revision ID: 010
Revises: 009_add_permissions
Create Date: 2024-12-15 22:50:00.000000

This migration adds columns that were missed due to branching migrations.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '010_fix_missing_columns'
down_revision = '009_add_permissions'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # ========== stores 表缺失字段 ==========
    if not column_exists('stores', 'password'):
        op.add_column('stores', sa.Column('password', sa.String(100), nullable=True, comment='门店密码'))
    
    if not column_exists('stores', 'email'):
        op.add_column('stores', sa.Column('email', sa.String(100), nullable=True, comment='邮箱'))
    
    if not column_exists('stores', 'logo'):
        op.add_column('stores', sa.Column('logo', sa.String(255), nullable=True, comment='门店logo'))
    
    if not column_exists('stores', 'theme_style'):
        op.add_column('stores', sa.Column('theme_style', sa.String(50), nullable=True, comment='风格选择'))
    
    # ========== departments 表缺失字段 ==========
    if not column_exists('departments', 'store_id'):
        op.add_column('departments', sa.Column('store_id', sa.String(36), nullable=True, comment='默认门店ID'))
        try:
            op.create_foreign_key('fk_departments_store_id', 'departments', 'stores', ['store_id'], ['id'])
        except:
            pass
        try:
            op.create_index('ix_departments_store_id', 'departments', ['store_id'])
        except:
            pass
    
    if not column_exists('departments', 'tag'):
        op.add_column('departments', sa.Column('tag', sa.String(100), nullable=True, comment='科室标签'))
    
    if not column_exists('departments', 'enable_banner'):
        op.add_column('departments', sa.Column('enable_banner', sa.Integer, server_default='0', comment='是否开放banner 0禁用 1启用'))
    
    if not column_exists('departments', 'enable_intro'):
        op.add_column('departments', sa.Column('enable_intro', sa.Integer, server_default='0', comment='是否开放科室简介 0禁用 1启用'))
    
    if not column_exists('departments', 'is_final'):
        op.add_column('departments', sa.Column('is_final', sa.Integer, server_default='0', comment='是否终极科室 0否 1是'))
    
    if not column_exists('departments', 'is_recommended'):
        op.add_column('departments', sa.Column('is_recommended', sa.Integer, server_default='0', comment='是否推荐 0否 1是'))
    
    if not column_exists('departments', 'banner_image'):
        op.add_column('departments', sa.Column('banner_image', sa.String(500), nullable=True, comment='banner图片URL'))
    
    if not column_exists('departments', 'icon'):
        op.add_column('departments', sa.Column('icon', sa.String(500), nullable=True, comment='科室图标URL'))
    
    if not column_exists('departments', 'intro_images'):
        op.add_column('departments', sa.Column('intro_images', sa.Text, nullable=True, comment='简介图片集JSON'))
    
    if not column_exists('departments', 'intro_content'):
        op.add_column('departments', sa.Column('intro_content', sa.Text, nullable=True, comment='富文本简介'))
    
    if not column_exists('departments', 'features'):
        op.add_column('departments', sa.Column('features', sa.Text, nullable=True, comment='科室特色JSON数组'))
    
    if not column_exists('departments', 'appointment_notice'):
        op.add_column('departments', sa.Column('appointment_notice', sa.Text, nullable=True, comment='预约须知'))
    
    if not column_exists('departments', 'phone'):
        op.add_column('departments', sa.Column('phone', sa.String(20), nullable=True, comment='科室电话'))
    
    if not column_exists('departments', 'location'):
        op.add_column('departments', sa.Column('location', sa.String(100), nullable=True, comment='位置/楼层'))
    
    if not column_exists('departments', 'working_hours'):
        op.add_column('departments', sa.Column('working_hours', sa.String(200), nullable=True, comment='工作时间'))
    
    # ========== doctors 表缺失字段 ==========
    if not column_exists('doctors', 'use_fee_template'):
        op.add_column('doctors', sa.Column('use_fee_template', sa.Integer, server_default='0', comment='是否使用诊费模板 0否 1是'))


def downgrade() -> None:
    # stores
    if column_exists('stores', 'theme_style'):
        op.drop_column('stores', 'theme_style')
    if column_exists('stores', 'logo'):
        op.drop_column('stores', 'logo')
    if column_exists('stores', 'email'):
        op.drop_column('stores', 'email')
    if column_exists('stores', 'password'):
        op.drop_column('stores', 'password')
    
    # departments
    if column_exists('departments', 'working_hours'):
        op.drop_column('departments', 'working_hours')
    if column_exists('departments', 'location'):
        op.drop_column('departments', 'location')
    if column_exists('departments', 'phone'):
        op.drop_column('departments', 'phone')
    if column_exists('departments', 'appointment_notice'):
        op.drop_column('departments', 'appointment_notice')
    if column_exists('departments', 'features'):
        op.drop_column('departments', 'features')
    if column_exists('departments', 'intro_content'):
        op.drop_column('departments', 'intro_content')
    if column_exists('departments', 'intro_images'):
        op.drop_column('departments', 'intro_images')
    if column_exists('departments', 'icon'):
        op.drop_column('departments', 'icon')
    if column_exists('departments', 'banner_image'):
        op.drop_column('departments', 'banner_image')
    if column_exists('departments', 'is_recommended'):
        op.drop_column('departments', 'is_recommended')
    if column_exists('departments', 'is_final'):
        op.drop_column('departments', 'is_final')
    if column_exists('departments', 'enable_intro'):
        op.drop_column('departments', 'enable_intro')
    if column_exists('departments', 'enable_banner'):
        op.drop_column('departments', 'enable_banner')
    if column_exists('departments', 'tag'):
        op.drop_column('departments', 'tag')
    if column_exists('departments', 'store_id'):
        try:
            op.drop_index('ix_departments_store_id', 'departments')
        except:
            pass
        try:
            op.drop_constraint('fk_departments_store_id', 'departments', type_='foreignkey')
        except:
            pass
        op.drop_column('departments', 'store_id')
    
    # doctors
    if column_exists('doctors', 'use_fee_template'):
        op.drop_column('doctors', 'use_fee_template')

