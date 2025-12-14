"""add new fields to doctors table

Revision ID: 002
Revises: 001_add_new_tables
Create Date: 2024-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_doctor_fields'
down_revision = '001_add_new_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加门店关联字段
    op.add_column('doctors', sa.Column('store_id', sa.String(36), nullable=True, comment='所属门店ID'))
    op.create_foreign_key('fk_doctors_store_id', 'doctors', 'stores', ['store_id'], ['id'])
    op.create_index('ix_doctors_store_id', 'doctors', ['store_id'])
    
    # 添加登录账号字段
    op.add_column('doctors', sa.Column('username', sa.String(50), nullable=True, comment='医生登录账号'))
    op.create_index('ix_doctors_username', 'doctors', ['username'], unique=True)
    
    # 添加性别字段
    op.add_column('doctors', sa.Column('gender', sa.Integer, server_default='1', comment='性别 0女 1男'))
    
    # 添加banner图字段
    op.add_column('doctors', sa.Column('banner', sa.String(255), nullable=True, comment='医生banner图URL'))
    
    # 添加医龄字段
    op.add_column('doctors', sa.Column('years_of_experience', sa.Integer, server_default='0', comment='医龄(年)'))
    
    # 添加资质信息字段
    op.add_column('doctors', sa.Column('education', sa.String(50), nullable=True, comment='学历'))
    op.add_column('doctors', sa.Column('graduate_school', sa.String(100), nullable=True, comment='毕业院校'))
    op.add_column('doctors', sa.Column('license_number', sa.String(100), nullable=True, comment='执业证书编号'))
    op.add_column('doctors', sa.Column('license_image', sa.String(255), nullable=True, comment='执业证书图片URL'))
    op.add_column('doctors', sa.Column('honors', sa.Text, nullable=True, comment='所获荣誉'))
    
    # 添加坐诊设置字段
    op.add_column('doctors', sa.Column('schedule_desc', sa.String(255), nullable=True, comment='坐诊时间说明'))
    op.add_column('doctors', sa.Column('max_daily_appointments', sa.Integer, server_default='0', comment='每日最大接诊量,0表示不限制'))
    op.add_column('doctors', sa.Column('online_consult_enabled', sa.Integer, server_default='0', comment='是否支持在线问诊 0否 1是'))
    op.add_column('doctors', sa.Column('online_consult_fee', sa.Numeric(10, 2), server_default='0', comment='在线问诊费用'))
    
    # 添加展示设置字段
    op.add_column('doctors', sa.Column('page_style', sa.Integer, server_default='1', comment='页面风格 1/2/3'))
    op.add_column('doctors', sa.Column('promo_video', sa.String(255), nullable=True, comment='宣传视频URL'))
    op.add_column('doctors', sa.Column('tags', sa.String(255), nullable=True, comment='标签,逗号分隔'))


def downgrade() -> None:
    # 删除展示设置字段
    op.drop_column('doctors', 'tags')
    op.drop_column('doctors', 'promo_video')
    op.drop_column('doctors', 'page_style')
    
    # 删除坐诊设置字段
    op.drop_column('doctors', 'online_consult_fee')
    op.drop_column('doctors', 'online_consult_enabled')
    op.drop_column('doctors', 'max_daily_appointments')
    op.drop_column('doctors', 'schedule_desc')
    
    # 删除资质信息字段
    op.drop_column('doctors', 'honors')
    op.drop_column('doctors', 'license_image')
    op.drop_column('doctors', 'license_number')
    op.drop_column('doctors', 'graduate_school')
    op.drop_column('doctors', 'education')
    
    # 删除医龄字段
    op.drop_column('doctors', 'years_of_experience')
    
    # 删除banner图字段
    op.drop_column('doctors', 'banner')
    
    # 删除性别字段
    op.drop_column('doctors', 'gender')
    
    # 删除登录账号字段
    op.drop_index('ix_doctors_username', 'doctors')
    op.drop_column('doctors', 'username')
    
    # 删除门店关联字段
    op.drop_index('ix_doctors_store_id', 'doctors')
    op.drop_constraint('fk_doctors_store_id', 'doctors', type_='foreignkey')
    op.drop_column('doctors', 'store_id')

