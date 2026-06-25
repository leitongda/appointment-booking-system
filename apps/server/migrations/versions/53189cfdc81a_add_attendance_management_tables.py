"""add attendance management tables

Revision ID: 53189cfdc81a
Revises: 07917442d4e3
Create Date: 2026-06-25 21:08:12.147395

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '53189cfdc81a'
down_revision = '07917442d4e3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- attendance_shifts ---
    op.create_table('attendance_shifts',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('tenant_id', sa.String(length=36), nullable=True, comment='租户ID'),
    sa.Column('name', sa.String(length=100), nullable=False, comment='班次名称'),
    sa.Column('code', sa.String(length=50), nullable=False, comment='班次代码'),
    sa.Column('start_time', sa.String(length=5), nullable=False, comment='上班时间 HH:MM'),
    sa.Column('end_time', sa.String(length=5), nullable=False, comment='下班时间 HH:MM'),
    sa.Column('break_start', sa.String(length=5), nullable=True, comment='午休开始 HH:MM'),
    sa.Column('break_end', sa.String(length=5), nullable=True, comment='午休结束 HH:MM'),
    sa.Column('grace_minutes', sa.Integer(), nullable=True, comment='迟到宽限分钟数'),
    sa.Column('late_threshold_minutes', sa.Integer(), nullable=True, comment='迟到判定阈值(分钟)'),
    sa.Column('early_threshold_minutes', sa.Integer(), nullable=True, comment='早退判定阈值(分钟)'),
    sa.Column('is_flexible', sa.Boolean(), nullable=True, comment='是否弹性工作制'),
    sa.Column('enabled', sa.Boolean(), nullable=True, comment='是否启用'),
    sa.Column('created_by', sa.String(length=36), nullable=True, comment='创建人ID'),
    sa.Column('updated_by', sa.String(length=36), nullable=True, comment='更新人ID'),
    sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
    sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'code', name='uq_attendance_shifts_tenant_code'),
    comment='考勤班次表'
    )
    op.create_index(op.f('ix_attendance_shifts_tenant_id'), 'attendance_shifts', ['tenant_id'], unique=False)

    # --- attendance_groups ---
    op.create_table('attendance_groups',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('tenant_id', sa.String(length=36), nullable=True, comment='租户ID'),
    sa.Column('name', sa.String(length=100), nullable=False, comment='签到组名称'),
    sa.Column('description', sa.Text(), nullable=True, comment='描述'),
    sa.Column('check_method', sa.String(length=20), nullable=True, comment='打卡方式: gps/wifi/device'),
    sa.Column('location_lat', sa.Float(), nullable=True, comment='纬度'),
    sa.Column('location_lng', sa.Float(), nullable=True, comment='经度'),
    sa.Column('location_radius', sa.Integer(), nullable=True, comment='打卡范围(米)'),
    sa.Column('wifi_ssid', sa.String(length=200), nullable=True, comment='WiFi SSID'),
    sa.Column('enabled', sa.Boolean(), nullable=True, comment='是否启用'),
    sa.Column('created_by', sa.String(length=36), nullable=True, comment='创建人ID'),
    sa.Column('updated_by', sa.String(length=36), nullable=True, comment='更新人ID'),
    sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
    sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    comment='签到组表'
    )
    op.create_index(op.f('ix_attendance_groups_tenant_id'), 'attendance_groups', ['tenant_id'], unique=False)

    # --- attendance_rules ---
    op.create_table('attendance_rules',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('tenant_id', sa.String(length=36), nullable=True, comment='租户ID'),
    sa.Column('name', sa.String(length=100), nullable=False, comment='规则名称'),
    sa.Column('description', sa.Text(), nullable=True, comment='描述'),
    sa.Column('late_policy', sa.String(length=20), nullable=True, comment='迟到策略: flexible/strict/ignore'),
    sa.Column('early_policy', sa.String(length=20), nullable=True, comment='早退策略: flexible/strict/ignore'),
    sa.Column('absent_policy', sa.String(length=20), nullable=True, comment='缺勤策略: strict/ignore'),
    sa.Column('overtime_enabled', sa.Boolean(), nullable=True, comment='是否启用加班计算'),
    sa.Column('overtime_min_minutes', sa.Integer(), nullable=True, comment='加班最小分钟数'),
    sa.Column('enabled', sa.Boolean(), nullable=True, comment='是否启用'),
    sa.Column('created_by', sa.String(length=36), nullable=True, comment='创建人ID'),
    sa.Column('updated_by', sa.String(length=36), nullable=True, comment='更新人ID'),
    sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
    sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    comment='考勤规则表'
    )
    op.create_index(op.f('ix_attendance_rules_tenant_id'), 'attendance_rules', ['tenant_id'], unique=False)

    # --- attendance_group_members (depends on attendance_groups) ---
    op.create_table('attendance_group_members',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('group_id', sa.String(length=36), nullable=False, comment='签到组ID'),
    sa.Column('account_id', sa.String(length=36), nullable=False, comment='账号ID'),
    sa.Column('tenant_id', sa.String(length=36), nullable=True, comment='租户ID'),
    sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['group_id'], ['attendance_groups.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('group_id', 'account_id', name='uq_attendance_group_member'),
    comment='签到组成员关联表'
    )
    op.create_index(op.f('ix_attendance_group_members_tenant_id'), 'attendance_group_members', ['tenant_id'], unique=False)

    # --- attendance_records (depends on attendance_shifts, attendance_groups) ---
    op.create_table('attendance_records',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('tenant_id', sa.String(length=36), nullable=True, comment='租户ID'),
    sa.Column('account_id', sa.String(length=36), nullable=False, comment='账号ID'),
    sa.Column('shift_id', sa.String(length=36), nullable=True, comment='班次ID'),
    sa.Column('group_id', sa.String(length=36), nullable=True, comment='签到组ID'),
    sa.Column('check_date', sa.Date(), nullable=False, comment='打卡日期'),
    sa.Column('check_in_time', sa.DateTime(), nullable=True, comment='签到时间'),
    sa.Column('check_out_time', sa.DateTime(), nullable=True, comment='签退时间'),
    sa.Column('check_in_lat', sa.Float(), nullable=True, comment='签到纬度'),
    sa.Column('check_in_lng', sa.Float(), nullable=True, comment='签到经度'),
    sa.Column('check_out_lat', sa.Float(), nullable=True, comment='签退纬度'),
    sa.Column('check_out_lng', sa.Float(), nullable=True, comment='签退经度'),
    sa.Column('check_in_device', sa.String(length=200), nullable=True, comment='签到设备信息'),
    sa.Column('check_out_device', sa.String(length=200), nullable=True, comment='签退设备信息'),
    sa.Column('status', sa.String(length=20), nullable=True, comment='状态: normal/late/early/absent/leave/field_work'),
    sa.Column('late_minutes', sa.Integer(), nullable=True, comment='迟到分钟数'),
    sa.Column('early_minutes', sa.Integer(), nullable=True, comment='早退分钟数'),
    sa.Column('work_hours', sa.Float(), nullable=True, comment='工作时长(小时)'),
    sa.Column('remark', sa.Text(), nullable=True, comment='备注'),
    sa.Column('created_by', sa.String(length=36), nullable=True, comment='创建人ID'),
    sa.Column('updated_by', sa.String(length=36), nullable=True, comment='更新人ID'),
    sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
    sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
    sa.ForeignKeyConstraint(['group_id'], ['attendance_groups.id'], ),
    sa.ForeignKeyConstraint(['shift_id'], ['attendance_shifts.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('account_id', 'check_date', name='uq_attendance_record_account_date'),
    comment='考勤打卡记录表'
    )
    op.create_index(op.f('ix_attendance_records_account_id'), 'attendance_records', ['account_id'], unique=False)
    op.create_index(op.f('ix_attendance_records_tenant_id'), 'attendance_records', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_attendance_records_tenant_id'), table_name='attendance_records')
    op.drop_index(op.f('ix_attendance_records_account_id'), table_name='attendance_records')
    op.drop_table('attendance_records')

    op.drop_index(op.f('ix_attendance_group_members_tenant_id'), table_name='attendance_group_members')
    op.drop_table('attendance_group_members')

    op.drop_index(op.f('ix_attendance_rules_tenant_id'), table_name='attendance_rules')
    op.drop_table('attendance_rules')

    op.drop_index(op.f('ix_attendance_groups_tenant_id'), table_name='attendance_groups')
    op.drop_table('attendance_groups')

    op.drop_index(op.f('ix_attendance_shifts_tenant_id'), table_name='attendance_shifts')
    op.drop_table('attendance_shifts')
