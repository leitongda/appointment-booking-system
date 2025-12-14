"""add new fields to departments table

Revision ID: 004
Revises: 003_add_store_fields
Create Date: 2024-12-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_add_department_fields'
down_revision = '003_add_store_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 基础配置字段
    op.add_column('departments', sa.Column('store_id', sa.String(36), nullable=True, comment='默认门店ID'))
    op.create_foreign_key('fk_departments_store_id', 'departments', 'stores', ['store_id'], ['id'])
    op.create_index('ix_departments_store_id', 'departments', ['store_id'])
    
    op.add_column('departments', sa.Column('tag', sa.String(100), nullable=True, comment='科室标签'))
    op.add_column('departments', sa.Column('enable_banner', sa.Integer, server_default='0', comment='是否开放banner 0禁用 1启用'))
    op.add_column('departments', sa.Column('enable_intro', sa.Integer, server_default='0', comment='是否开放科室简介 0禁用 1启用'))
    op.add_column('departments', sa.Column('is_final', sa.Integer, server_default='0', comment='是否终极科室 0否 1是'))
    op.add_column('departments', sa.Column('is_recommended', sa.Integer, server_default='0', comment='是否推荐 0否 1是'))
    
    # 图片资源字段
    op.add_column('departments', sa.Column('banner_image', sa.String(500), nullable=True, comment='banner图片URL'))
    op.add_column('departments', sa.Column('icon', sa.String(500), nullable=True, comment='科室图标URL'))
    op.add_column('departments', sa.Column('intro_images', sa.Text, nullable=True, comment='简介图片集JSON'))
    
    # 详情内容字段
    op.add_column('departments', sa.Column('intro_content', sa.Text, nullable=True, comment='富文本简介'))
    op.add_column('departments', sa.Column('features', sa.Text, nullable=True, comment='科室特色JSON数组'))
    op.add_column('departments', sa.Column('appointment_notice', sa.Text, nullable=True, comment='预约须知'))
    
    # 联系信息字段
    op.add_column('departments', sa.Column('phone', sa.String(20), nullable=True, comment='科室电话'))
    op.add_column('departments', sa.Column('location', sa.String(100), nullable=True, comment='位置/楼层'))
    op.add_column('departments', sa.Column('working_hours', sa.String(200), nullable=True, comment='工作时间'))


def downgrade() -> None:
    # 删除联系信息字段
    op.drop_column('departments', 'working_hours')
    op.drop_column('departments', 'location')
    op.drop_column('departments', 'phone')
    
    # 删除详情内容字段
    op.drop_column('departments', 'appointment_notice')
    op.drop_column('departments', 'features')
    op.drop_column('departments', 'intro_content')
    
    # 删除图片资源字段
    op.drop_column('departments', 'intro_images')
    op.drop_column('departments', 'icon')
    op.drop_column('departments', 'banner_image')
    
    # 删除基础配置字段
    op.drop_column('departments', 'is_recommended')
    op.drop_column('departments', 'is_final')
    op.drop_column('departments', 'enable_intro')
    op.drop_column('departments', 'enable_banner')
    op.drop_column('departments', 'tag')
    
    # 删除门店关联字段
    op.drop_index('ix_departments_store_id', 'departments')
    op.drop_constraint('fk_departments_store_id', 'departments', type_='foreignkey')
    op.drop_column('departments', 'store_id')
