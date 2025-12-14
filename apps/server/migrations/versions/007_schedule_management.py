"""add custom schedule, rest day, schedule suspension tables

Revision ID: 007
Revises: 006_patient_management
Create Date: 2024-12-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007_schedule_management'
down_revision = '006_patient_management'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建自定义排班表
    op.create_table(
        'custom_schedules',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=False, comment='门店ID'),
        sa.Column('department_id', sa.String(36), sa.ForeignKey('departments.id'), nullable=False, comment='科室ID'),
        sa.Column('doctor_id', sa.String(36), sa.ForeignKey('doctors.id'), nullable=False, comment='医生ID'),
        sa.Column('schedule_date', sa.Date, nullable=False, comment='排班日期'),
        sa.Column('start_time', sa.Time, nullable=False, comment='开始时间'),
        sa.Column('end_time', sa.Time, nullable=False, comment='结束时间'),
        sa.Column('appointment_type', sa.String(20), nullable=False, comment='预约类型'),
        sa.Column('max_patients', sa.Integer, server_default='1', comment='预约人数'),
        sa.Column('booked_count', sa.Integer, server_default='0', comment='已预约数'),
        sa.Column('status', sa.Integer, server_default='1', comment='状态: 0停用 1启用'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_custom_schedules_store_id', 'custom_schedules', ['store_id'])
    op.create_index('ix_custom_schedules_doctor_id', 'custom_schedules', ['doctor_id'])
    op.create_index('ix_custom_schedules_schedule_date', 'custom_schedules', ['schedule_date'])
    
    # 创建休息日表
    op.create_table(
        'rest_days',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=False, comment='门店ID'),
        sa.Column('doctor_ids', sa.Text, nullable=True, comment='医生ID列表JSON数组'),
        sa.Column('reason', sa.String(255), nullable=True, comment='休息原因'),
        sa.Column('start_date', sa.Date, nullable=False, comment='开始日期'),
        sa.Column('end_date', sa.Date, nullable=False, comment='结束日期'),
        sa.Column('status', sa.Integer, server_default='1', comment='状态: 0已取消 1生效中'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_rest_days_store_id', 'rest_days', ['store_id'])
    op.create_index('ix_rest_days_start_date', 'rest_days', ['start_date'])
    op.create_index('ix_rest_days_end_date', 'rest_days', ['end_date'])
    
    # 创建停诊记录表
    op.create_table(
        'schedule_suspensions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=False, comment='门店ID'),
        sa.Column('doctor_id', sa.String(36), sa.ForeignKey('doctors.id'), nullable=False, comment='医生ID'),
        sa.Column('title', sa.String(100), nullable=False, comment='停诊标题'),
        sa.Column('suspension_date', sa.Date, nullable=False, comment='停诊日期'),
        sa.Column('schedule_ids', sa.Text, nullable=True, comment='选中的排班ID JSON数组'),
        sa.Column('time_slots', sa.Text, nullable=True, comment='选中的时段 JSON数组'),
        sa.Column('status', sa.Integer, server_default='1', comment='状态: 0已取消 1生效中'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_schedule_suspensions_store_id', 'schedule_suspensions', ['store_id'])
    op.create_index('ix_schedule_suspensions_doctor_id', 'schedule_suspensions', ['doctor_id'])
    op.create_index('ix_schedule_suspensions_suspension_date', 'schedule_suspensions', ['suspension_date'])


def downgrade() -> None:
    # 删除停诊记录表
    op.drop_index('ix_schedule_suspensions_suspension_date', 'schedule_suspensions')
    op.drop_index('ix_schedule_suspensions_doctor_id', 'schedule_suspensions')
    op.drop_index('ix_schedule_suspensions_store_id', 'schedule_suspensions')
    op.drop_table('schedule_suspensions')
    
    # 删除休息日表
    op.drop_index('ix_rest_days_end_date', 'rest_days')
    op.drop_index('ix_rest_days_start_date', 'rest_days')
    op.drop_index('ix_rest_days_store_id', 'rest_days')
    op.drop_table('rest_days')
    
    # 删除自定义排班表
    op.drop_index('ix_custom_schedules_schedule_date', 'custom_schedules')
    op.drop_index('ix_custom_schedules_doctor_id', 'custom_schedules')
    op.drop_index('ix_custom_schedules_store_id', 'custom_schedules')
    op.drop_table('custom_schedules')
