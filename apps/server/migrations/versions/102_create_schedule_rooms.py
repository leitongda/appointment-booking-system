"""create schedule_rooms table + add room_id to schedules

Revision ID: 102
Revises: 101
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = '102'
down_revision = '101'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 schedule_rooms 表
    op.create_table(
        'schedule_rooms',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=False, comment='租户ID'),
        sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=False, comment='门店ID'),
        sa.Column('name', sa.String(100), nullable=False, comment='诊室名称'),
        sa.Column('room_number', sa.String(50), nullable=True, comment='房间号'),
        sa.Column('floor', sa.String(20), nullable=True, comment='楼层'),
        sa.Column('department_id', sa.String(36), sa.ForeignKey('departments.id'), nullable=True, comment='所属科室'),
        sa.Column('capacity', sa.Integer(), server_default='1', comment='容量'),
        sa.Column('status', sa.Integer(), server_default='1', comment='状态 0禁用 1启用'),
        sa.Column('remark', sa.String(500), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), comment='更新时间'),
        sa.Column('created_by', sa.String(36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(36), nullable=True, comment='更新人ID'),
        sa.Index('ix_schedule_rooms_tenant_id', 'tenant_id'),
        sa.Index('ix_schedule_rooms_store_id', 'store_id'),
        sa.Index('ix_schedule_rooms_department_id', 'department_id'),
        sa.Index('uix_room_tenant_store_name', 'tenant_id', 'store_id', 'name', unique=True),
        comment='诊室表',
    )

    # 给 schedules 表加 room_id 列
    op.add_column(
        'schedules',
        sa.Column('room_id', sa.String(36), sa.ForeignKey('schedule_rooms.id'), nullable=True, comment='诊室ID'),
    )
    op.create_index('ix_schedules_room_id', 'schedules', ['room_id'])


def downgrade() -> None:
    op.drop_index('ix_schedules_room_id', table_name='schedules')
    op.drop_column('schedules', 'room_id')
    op.drop_table('schedule_rooms')
