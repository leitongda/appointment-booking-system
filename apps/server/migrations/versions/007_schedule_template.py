"""add schedule template and extend schedules

Revision ID: 007
Revises: 006_patient_management
Create Date: 2024-12-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007_schedule_template'
down_revision = '006_patient_management'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建排班模板表
    op.create_table(
        'schedule_templates',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, comment='模板名称'),
        sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=False, comment='门店ID'),
        sa.Column('doctor_id', sa.String(36), sa.ForeignKey('doctors.id'), nullable=False, comment='医生ID'),
        sa.Column('department_id', sa.String(36), sa.ForeignKey('departments.id'), nullable=False, comment='科室ID'),
        sa.Column('weekday', sa.Integer, nullable=False, comment='星期 1-7'),
        sa.Column('appointment_type', sa.String(20), server_default='normal', comment='预约类型: urgent/normal/expert/medical_insurance/self_pay'),
        sa.Column('start_time', sa.Time, nullable=False, comment='开始时间'),
        sa.Column('end_time', sa.Time, nullable=False, comment='结束时间'),
        sa.Column('total_slots', sa.Integer, server_default='10', comment='班次人数'),
        sa.Column('schedule_mode', sa.String(50), server_default='weekly', comment='排班方式'),
        sa.Column('status', sa.Integer, server_default='1', comment='状态: 0禁用 1启用'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_schedule_templates_store_id', 'schedule_templates', ['store_id'])
    op.create_index('ix_schedule_templates_doctor_id', 'schedule_templates', ['doctor_id'])
    op.create_index('ix_schedule_templates_department_id', 'schedule_templates', ['department_id'])
    
    # 扩展 schedules 表 - 添加门店ID、预约类型、来源模板ID字段
    op.add_column('schedules', sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=True, comment='门店ID'))
    op.add_column('schedules', sa.Column('appointment_type', sa.String(20), server_default='normal', comment='预约类型'))
    op.add_column('schedules', sa.Column('template_id', sa.String(36), sa.ForeignKey('schedule_templates.id'), nullable=True, comment='来源模板ID'))
    
    op.create_index('ix_schedules_store_id', 'schedules', ['store_id'])
    op.create_index('ix_schedules_template_id', 'schedules', ['template_id'])


def downgrade() -> None:
    # 删除 schedules 表的索引和新字段
    op.drop_index('ix_schedules_template_id', 'schedules')
    op.drop_index('ix_schedules_store_id', 'schedules')
    op.drop_column('schedules', 'template_id')
    op.drop_column('schedules', 'appointment_type')
    op.drop_column('schedules', 'store_id')
    
    # 删除排班模板表
    op.drop_index('ix_schedule_templates_department_id', 'schedule_templates')
    op.drop_index('ix_schedule_templates_doctor_id', 'schedule_templates')
    op.drop_index('ix_schedule_templates_store_id', 'schedule_templates')
    op.drop_table('schedule_templates')
