"""add doctor booking settings table

Revision ID: 005
Revises: 004_add_consultation_fee
Create Date: 2024-01-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005_add_doctor_booking_settings'
down_revision = '004_add_consultation_fee'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建医生预约设置表
    op.create_table(
        'doctor_booking_settings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=False, comment='门店ID'),
        sa.Column('doctor_id', sa.String(36), sa.ForeignKey('doctors.id'), nullable=False, comment='医生ID'),
        sa.Column('booking_start_offset', sa.Integer, server_default='0', comment='预约开始偏移天数，0表示当天'),
        sa.Column('booking_range_days', sa.Integer, server_default='14', comment='预约范围天数，1-90天'),
        sa.Column('release_time', sa.String(5), server_default='00:00', comment='放号时间 HH:mm格式'),
        sa.Column('status', sa.Integer, server_default='1', comment='状态: 0禁用 1启用'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # 创建索引
    op.create_index('ix_doctor_booking_settings_store', 'doctor_booking_settings', ['store_id'])
    op.create_index('ix_doctor_booking_settings_doctor', 'doctor_booking_settings', ['doctor_id'])
    # 唯一索引：同一门店同一医生只能有一条设置
    op.create_index(
        'uix_store_doctor',
        'doctor_booking_settings',
        ['store_id', 'doctor_id'],
        unique=True
    )


def downgrade() -> None:
    # 删除索引
    op.drop_index('uix_store_doctor', 'doctor_booking_settings')
    op.drop_index('ix_doctor_booking_settings_doctor', 'doctor_booking_settings')
    op.drop_index('ix_doctor_booking_settings_store', 'doctor_booking_settings')
    # 删除表
    op.drop_table('doctor_booking_settings')
