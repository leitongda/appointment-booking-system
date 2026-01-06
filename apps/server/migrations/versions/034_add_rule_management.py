"""add rule management tables

Revision ID: 034_rule_management
Revises: 033_store_settings
Create Date: 2026-01-05

添加规则管理系统核心表:
- shift_types: 班次类型表
- rule_sets: 规则组表
- rule_set_shift_types: 关联表
- rule_windows: 时间窗配置表
- rule_booking_policies: 预约策略表
- rule_checkin_policies: 签到策略表
- rule_capacity_policies: 容量策略表
- appointment_checkins: 签到日志表

扩展现有表:
- schedules: 新增 shift_type_id, start_at, end_at, timezone 字段
- appointments: 新增规则快照字段
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '034_rule_management'
down_revision = '033_store_settings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==================== 新建表 ====================

    # 1. 创建班次类型表
    op.create_table(
        'shift_types',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('code', sa.String(50), nullable=False, unique=True, comment='类型代码: OPD/CHECKUP/EXAM'),
        sa.Column('name', sa.String(100), nullable=False, comment='类型名称'),
        sa.Column('description', sa.Text, comment='描述'),
        sa.Column('enabled', sa.Boolean, nullable=False, default=True, comment='是否启用'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(36), comment='创建人ID'),
        sa.Column('updated_by', sa.String(36), comment='更新人ID'),
        comment='班次类型表'
    )

    # 插入默认班次类型
    op.execute("""
        INSERT INTO shift_types (id, code, name, description, enabled) VALUES
        ('550e8400-e29b-41d4-a716-446655440001', 'OPD', '门诊', '普通门诊服务', true),
        ('550e8400-e29b-41d4-a716-446655440002', 'CHECKUP', '体检', '体检服务', true),
        ('550e8400-e29b-41d4-a716-446655440003', 'EXAM', '检查', '检查项目', true),
        ('550e8400-e29b-41d4-a716-446655440004', 'NURSING', '护理', '护理服务', true),
        ('550e8400-e29b-41d4-a716-446655440005', 'SPECIAL', '特需', '特需服务', true)
    """)

    # 2. 创建规则组表
    op.create_table(
        'rule_sets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False, comment='规则组名称'),
        sa.Column('enabled', sa.Boolean, nullable=False, default=True, comment='是否启用'),
        sa.Column('priority', sa.Integer, nullable=False, default=100, comment='优先级(越小越优先)'),
        # 默认口径
        sa.Column('time_source', sa.String(20), nullable=False, default='SERVER', comment='时间来源: SERVER/CLIENT'),
        sa.Column('timezone_source', sa.String(20), nullable=False, default='HOSPITAL', comment='时区来源: HOSPITAL/SHIFT/USER'),
        sa.Column('compare_precision', sa.String(20), nullable=False, default='SECOND', comment='比较精度: SECOND/MILLISECOND/MINUTE'),
        sa.Column('default_open_inclusive', sa.Boolean, nullable=False, default=True, comment='默认开放边界包含'),
        sa.Column('default_close_inclusive', sa.Boolean, nullable=False, default=True, comment='默认截止边界包含'),
        sa.Column('rounding_mode', sa.String(30), nullable=False, default='NONE', comment='取整模式'),
        sa.Column('clock_skew_tolerance_sec', sa.Integer, nullable=False, default=5, comment='时钟偏差容忍度(秒)'),
        sa.Column('description', sa.Text, comment='描述'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(36), comment='创建人ID'),
        sa.Column('updated_by', sa.String(36), comment='更新人ID'),
        comment='规则组表'
    )

    # 索引：加速查询启用的规则组
    op.create_index('idx_rule_sets_enabled_priority', 'rule_sets', ['enabled', 'priority'])

    # 3. 创建规则组与班次类型关联表
    op.create_table(
        'rule_set_shift_types',
        sa.Column('rule_set_id', sa.String(36), primary_key=True),
        sa.Column('shift_type_id', sa.String(36), primary_key=True),
        sa.ForeignKeyConstraint(['rule_set_id'], ['rule_sets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['shift_type_id'], ['shift_types.id'], ondelete='CASCADE'),
        comment='规则组与班次类型关联表'
    )

    op.create_index('idx_rsst_shift_type', 'rule_set_shift_types', ['shift_type_id'])

    # 4. 创建时间窗配置表
    op.create_table(
        'rule_windows',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('rule_set_id', sa.String(36), sa.ForeignKey('rule_sets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action', sa.String(30), nullable=False, comment='动作类型: BOOK/CHECKIN/CANCEL/HOLD_RELEASE'),
        sa.Column('reference_point', sa.String(50), nullable=False, comment='参考点: SHIFT_START/SHIFT_END/BOOKING_CREATED_AT'),
        sa.Column('open_offset_sec', sa.Integer, nullable=False, comment='开放偏移(秒),可负可正'),
        sa.Column('close_offset_sec', sa.Integer, nullable=False, comment='截止偏移(秒),可负可正'),
        sa.Column('open_inclusive', sa.Boolean, comment='开放边界包含,NULL则使用规则组默认值'),
        sa.Column('close_inclusive', sa.Boolean, comment='截止边界包含,NULL则使用规则组默认值'),
        sa.Column('fail_policy', sa.String(30), nullable=False, default='REJECT', comment='失败策略: REJECT/ALLOW_WITH_TAG/AUTO_TO_WAITLIST'),
        sa.Column('fail_tag', sa.String(100), comment='失败标签'),
        sa.Column('enabled', sa.Boolean, nullable=False, default=True, comment='是否启用'),
        sa.Column('description', sa.Text, comment='描述'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(36), comment='创建人ID'),
        sa.Column('updated_by', sa.String(36), comment='更新人ID'),
        comment='时间窗配置表'
    )

    op.create_index('idx_rule_windows_rs', 'rule_windows', ['rule_set_id', 'enabled'])

    # 5. 创建预约策略表
    op.create_table(
        'rule_booking_policies',
        sa.Column('rule_set_id', sa.String(36), sa.ForeignKey('rule_sets.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('require_auth', sa.Boolean, nullable=False, default=True, comment='是否要求登录'),
        sa.Column('require_patient_profile_complete', sa.Boolean, nullable=False, default=False, comment='是否要求档案完整'),
        sa.Column('per_user_per_shift', sa.Integer, nullable=False, default=1, comment='每用户每班次最大预约数'),
        sa.Column('per_user_per_day', sa.Integer, comment='每用户每天最大预约数'),
        sa.Column('per_user_per_week', sa.Integer, comment='每用户每周最大预约数'),
        sa.Column('conflict_same_shift', sa.String(20), nullable=False, default='REJECT', comment='同一班次冲突策略: REJECT/REPLACE'),
        sa.Column('conflict_overlap_time', sa.String(20), nullable=False, default='REJECT', comment='时间重叠冲突策略: REJECT/ALLOW'),
        sa.Column('conflict_same_type_same_day', sa.String(20), nullable=False, default='ALLOW', comment='同类型同日冲突策略: REJECT/ALLOW'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(36), comment='创建人ID'),
        sa.Column('updated_by', sa.String(36), comment='更新人ID'),
        comment='预约策略表'
    )

    # 6. 创建签到策略表
    op.create_table(
        'rule_checkin_policies',
        sa.Column('rule_set_id', sa.String(36), sa.ForeignKey('rule_sets.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('require_booking', sa.Boolean, nullable=False, default=True, comment='是否必须预约'),
        sa.Column('allow_onsite_booking', sa.Boolean, nullable=False, default=False, comment='是否允许现场补约'),
        sa.Column('max_times', sa.Integer, nullable=False, default=1, comment='允许签到次数'),
        sa.Column('audit_log', sa.Boolean, nullable=False, default=True, comment='是否记录审计日志'),
        sa.Column('grace_period_sec', sa.Integer, nullable=False, default=0, comment='宽限期(秒)'),
        sa.Column('after_grace_status', sa.String(30), comment='宽限后状态: LATE/ON_TIME'),
        sa.Column('no_checkin_after_close', sa.String(30), nullable=False, default='KEEP_BOOKED', comment='截止后未签到处理: KEEP_BOOKED/AUTO_CANCEL/ABSENT'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(36), comment='创建人ID'),
        sa.Column('updated_by', sa.String(36), comment='更新人ID'),
        comment='签到策略表'
    )

    # 7. 创建容量策略表
    op.create_table(
        'rule_capacity_policies',
        sa.Column('rule_set_id', sa.String(36), sa.ForeignKey('rule_sets.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('total_capacity', sa.Integer, nullable=False, default=0, comment='总容量,0表示不限制'),
        sa.Column('per_user_capacity', sa.Integer, nullable=False, default=1, comment='每用户容量'),
        sa.Column('waitlist_enabled', sa.Boolean, nullable=False, default=False, comment='是否启用候补'),
        sa.Column('waitlist_max_size', sa.Integer, nullable=False, default=0, comment='候补队列最大长度'),
        sa.Column('waitlist_promote_policy', sa.String(50), nullable=False, default='MANUAL', comment='候补递补策略: MANUAL/AUTO'),
        sa.Column('overbooking_enabled', sa.Boolean, nullable=False, default=False, comment='是否允许超额'),
        sa.Column('overbooking_max', sa.Integer, nullable=False, default=0, comment='超额最大数量'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(36), comment='创建人ID'),
        sa.Column('updated_by', sa.String(36), comment='更新人ID'),
        comment='容量策略表'
    )

    # 8. 创建签到日志表
    op.create_table(
        'appointment_checkins',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('appointment_id', sa.String(36), sa.ForeignKey('appointments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('checkin_time', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()'), comment='签到时间'),
        sa.Column('checkin_method', sa.String(30), nullable=False, comment='签到方式: QR_CODE/MANUAL/PHONE'),
        sa.Column('device_info', sa.String(200), comment='设备信息'),
        sa.Column('location_info', sa.String(200), comment='位置信息'),
        sa.Column('operator_id', sa.String(36), comment='操作人ID'),
        sa.Column('operator_type', sa.String(20), comment='操作人类型: USER/ADMIN/DOCTOR'),
        sa.Column('status', sa.String(20), nullable=False, default='SUCCESS', comment='状态: SUCCESS/FAILED/CANCELLED'),
        sa.Column('fail_reason', sa.String(200), comment='失败原因'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        comment='签到日志表'
    )

    op.create_index('idx_app_checkins_appointment', 'appointment_checkins', ['appointment_id'])
    op.create_index('idx_app_checkins_time', 'appointment_checkins', ['checkin_time'])

    # ==================== 扩展现有表 ====================

    # 9. 扩展 schedules 表
    op.add_column('schedules', sa.Column('shift_type_id', sa.String(36), sa.ForeignKey('shift_types.id'), comment='班次类型ID'))
    op.add_column('schedules', sa.Column('start_at', sa.TIMESTAMP(timezone=True), comment='带时区的开始时间'))
    op.add_column('schedules', sa.Column('end_at', sa.TIMESTAMP(timezone=True), comment='带时区的结束时间'))
    # timezone 列需要分步添加：先添加可空列，更新现有数据，再设置为 NOT NULL
    op.add_column('schedules', sa.Column('timezone', sa.String(50), nullable=True, comment='时区'))
    op.execute("UPDATE schedules SET timezone = 'Asia/Shanghai' WHERE timezone IS NULL")
    op.alter_column('schedules', 'timezone', nullable=False)

    op.create_index('idx_schedules_shift_type', 'schedules', ['shift_type_id'])

    # 10. 扩展 appointments 表
    op.add_column('appointments', sa.Column('rule_set_id', sa.String(36), sa.ForeignKey('rule_sets.id'), comment='绑定的规则组ID'))
    op.add_column('appointments', sa.Column('rule_set_version_id', sa.String(36), comment='绑定的规则版本ID'))
    op.add_column('appointments', sa.Column('book_open_at', sa.TIMESTAMP(timezone=True), comment='预约窗口开放时间(快照)'))
    op.add_column('appointments', sa.Column('book_close_at', sa.TIMESTAMP(timezone=True), comment='预约窗口截止时间(快照)'))
    op.add_column('appointments', sa.Column('checkin_open_at', sa.TIMESTAMP(timezone=True), comment='签到窗口开放时间(快照)'))
    op.add_column('appointments', sa.Column('checkin_close_at', sa.TIMESTAMP(timezone=True), comment='签到窗口截止时间(快照)'))
    op.add_column('appointments', sa.Column('cancel_open_at', sa.TIMESTAMP(timezone=True), comment='取消窗口开放时间(快照)'))
    op.add_column('appointments', sa.Column('cancel_close_at', sa.TIMESTAMP(timezone=True), comment='取消窗口截止时间(快照)'))
    op.add_column('appointments', sa.Column('checkin_count', sa.Integer, nullable=False, default=0, comment='签到次数'))
    op.add_column('appointments', sa.Column('last_checkin_at', sa.TIMESTAMP(timezone=True), comment='最后签到时间'))


def downgrade() -> None:
    # 按相反顺序删除

    # 删除 appointments 表新增字段
    op.drop_column('appointments', 'last_checkin_at')
    op.drop_column('appointments', 'checkin_count')
    op.drop_column('appointments', 'cancel_close_at')
    op.drop_column('appointments', 'cancel_open_at')
    op.drop_column('appointments', 'checkin_close_at')
    op.drop_column('appointments', 'checkin_open_at')
    op.drop_column('appointments', 'book_close_at')
    op.drop_column('appointments', 'book_open_at')
    op.drop_column('appointments', 'rule_set_version_id')
    op.drop_column('appointments', 'rule_set_id')

    # 删除 schedules 表新增字段
    op.drop_index('idx_schedules_shift_type', table_name='schedules')
    op.drop_column('schedules', 'timezone')
    op.drop_column('schedules', 'end_at')
    op.drop_column('schedules', 'start_at')
    op.drop_column('schedules', 'shift_type_id')

    # 删除签到日志表
    op.drop_index('idx_app_checkins_time', table_name='appointment_checkins')
    op.drop_index('idx_app_checkins_appointment', table_name='appointment_checkins')
    op.drop_table('appointment_checkins')

    # 删除策略表
    op.drop_table('rule_capacity_policies')
    op.drop_table('rule_checkin_policies')
    op.drop_table('rule_booking_policies')

    # 删除时间窗表
    op.drop_index('idx_rule_windows_rs', table_name='rule_windows')
    op.drop_table('rule_windows')

    # 删除关联表
    op.drop_index('idx_rsst_shift_type', table_name='rule_set_shift_types')
    op.drop_table('rule_set_shift_types')

    # 删除规则组表
    op.drop_index('idx_rule_sets_enabled_priority', table_name='rule_sets')
    op.drop_table('rule_sets')

    # 删除班次类型表
    op.drop_table('shift_types')
