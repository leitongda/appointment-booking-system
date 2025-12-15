"""merge multiple heads into single head

Revision ID: 011_merge_heads
Revises: 004_add_department_fields, 007_schedule_template, 010_fix_missing_columns
Create Date: 2024-12-15 23:00:00.000000

This migration merges three divergent branches:
- 004_add_department_fields (branch 1)
- 007_schedule_template (branch 2) 
- 010_fix_missing_columns (branch 3)

It also ensures all tables that might be missing are created.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '011_merge_heads'
down_revision = ('004_add_department_fields', '007_schedule_template', '010_fix_missing_columns')
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    if not table_exists(table_name):
        return False
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(table_name: str, index_name: str) -> bool:
    """检查索引是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    if not table_exists(table_name):
        return False
    indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def upgrade() -> None:
    """
    合并迁移 - 确保所有分支的变更都被应用
    """
    
    # ========== 确保 doctor_booking_settings 表存在 (来自 005) ==========
    if not table_exists('doctor_booking_settings'):
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
        
        if not index_exists('doctor_booking_settings', 'ix_doctor_booking_settings_store'):
            op.create_index('ix_doctor_booking_settings_store', 'doctor_booking_settings', ['store_id'])
        if not index_exists('doctor_booking_settings', 'ix_doctor_booking_settings_doctor'):
            op.create_index('ix_doctor_booking_settings_doctor', 'doctor_booking_settings', ['doctor_id'])
        if not index_exists('doctor_booking_settings', 'uix_store_doctor'):
            op.create_index(
                'uix_store_doctor',
                'doctor_booking_settings',
                ['store_id', 'doctor_id'],
                unique=True
            )
    
    # ========== 确保 consultation_fee 相关表存在 (来自 004_add_consultation_fee) ==========
    if not table_exists('consultation_fee_types'):
        op.create_table(
            'consultation_fee_types',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('name', sa.String(50), nullable=False, comment='诊费类型名称'),
            sa.Column('code', sa.String(50), nullable=True, comment='类型编码'),
            sa.Column('description', sa.String(255), nullable=True, comment='描述'),
            sa.Column('sort_order', sa.Integer, server_default='0', comment='排序'),
            sa.Column('status', sa.Integer, server_default='1', comment='状态: 0禁用 1启用'),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index('ix_consultation_fee_types_code', 'consultation_fee_types', ['code'], unique=True)
        
        # 插入默认诊费类型
        op.execute("""
            INSERT INTO consultation_fee_types (id, name, code, description, sort_order, status) VALUES
            (gen_random_uuid()::text, '专家', 'expert', '专家诊费', 1, 1),
            (gen_random_uuid()::text, '普通', 'normal', '普通诊费', 2, 1),
            (gen_random_uuid()::text, '加急', 'urgent', '加急诊费', 3, 1),
            (gen_random_uuid()::text, '医保', 'medical_insurance', '医保诊费', 4, 1),
            (gen_random_uuid()::text, '自费', 'self_pay', '自费诊费', 5, 1)
        """)
    
    if not table_exists('consultation_fee_templates'):
        op.create_table(
            'consultation_fee_templates',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('fee_type_id', sa.String(36), sa.ForeignKey('consultation_fee_types.id'), nullable=False, comment='诊费类型ID'),
            sa.Column('initial_fee', sa.Numeric(10, 2), server_default='0', comment='初诊金额'),
            sa.Column('follow_up_fee', sa.Numeric(10, 2), server_default='0', comment='复诊金额'),
            sa.Column('status', sa.Integer, server_default='1', comment='状态: 0禁用 1启用'),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index('ix_consultation_fee_templates_fee_type', 'consultation_fee_templates', ['fee_type_id'], unique=True)
    
    if not table_exists('doctor_consultation_fees'):
        op.create_table(
            'doctor_consultation_fees',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('doctor_id', sa.String(36), sa.ForeignKey('doctors.id'), nullable=False, comment='医生ID'),
            sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=False, comment='门店ID'),
            sa.Column('department_id', sa.String(36), sa.ForeignKey('departments.id'), nullable=False, comment='科室ID'),
            sa.Column('fee_type_id', sa.String(36), sa.ForeignKey('consultation_fee_types.id'), nullable=False, comment='诊费类型ID'),
            sa.Column('initial_fee', sa.Numeric(10, 2), server_default='0', comment='初诊金额'),
            sa.Column('follow_up_fee', sa.Numeric(10, 2), server_default='0', comment='复诊金额'),
            sa.Column('status', sa.Integer, server_default='1', comment='状态: 0禁用 1启用'),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index('ix_doctor_consultation_fees_doctor', 'doctor_consultation_fees', ['doctor_id'])
        op.create_index('ix_doctor_consultation_fees_store', 'doctor_consultation_fees', ['store_id'])
        op.create_index('ix_doctor_consultation_fees_department', 'doctor_consultation_fees', ['department_id'])
        op.create_index(
            'ix_doctor_consultation_fees_unique',
            'doctor_consultation_fees',
            ['doctor_id', 'store_id', 'department_id', 'fee_type_id'],
            unique=True
        )
    
    # ========== 确保 point_logs 表存在 (来自 006) ==========
    if not table_exists('point_logs'):
        op.create_table(
            'point_logs',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False, comment='用户ID'),
            sa.Column('change_amount', sa.Integer, nullable=False, comment='变更积分（正增负减）'),
            sa.Column('balance', sa.Integer, nullable=False, comment='变更后余额'),
            sa.Column('type', sa.Integer, server_default='4', comment='类型: 1消费 2充值 3赠送 4手动调整'),
            sa.Column('remark', sa.String(255), nullable=True, comment='备注'),
            sa.Column('operator_id', sa.String(36), nullable=True, comment='操作人ID'),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index('ix_point_logs_user_id', 'point_logs', ['user_id'])
    
    # ========== 确保 schedule_templates 表存在 (来自 007_schedule_template) ==========
    if not table_exists('schedule_templates'):
        op.create_table(
            'schedule_templates',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('name', sa.String(100), nullable=False, comment='模板名称'),
            sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=False, comment='门店ID'),
            sa.Column('doctor_id', sa.String(36), sa.ForeignKey('doctors.id'), nullable=False, comment='医生ID'),
            sa.Column('department_id', sa.String(36), sa.ForeignKey('departments.id'), nullable=False, comment='科室ID'),
            sa.Column('weekday', sa.Integer, nullable=False, comment='星期 1-7'),
            sa.Column('appointment_type', sa.String(20), server_default='normal', comment='预约类型'),
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
    
    # ========== 确保 custom_schedules 表存在 (来自 007_schedule_management) ==========
    if not table_exists('custom_schedules'):
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
    
    # ========== 确保 rest_days 表存在 (来自 007_schedule_management) ==========
    if not table_exists('rest_days'):
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
    
    # ========== 确保 schedule_suspensions 表存在 (来自 007_schedule_management) ==========
    if not table_exists('schedule_suspensions'):
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
    
    # ========== 确保 blacklists 表存在 (来自 008) ==========
    if not table_exists('blacklists'):
        op.create_table(
            'blacklists',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True, comment='用户ID，可选'),
            sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=True, comment='门店ID，可选'),
            sa.Column('keyword', sa.String(50), nullable=True, comment='手机号或身份证关键词'),
            sa.Column('reason', sa.String(500), nullable=True, comment='黑名单原因/备注'),
            sa.Column('no_show_count', sa.Integer, server_default='0', comment='爽约次数'),
            sa.Column('source', sa.Integer, server_default='1', comment='来源: 1手动添加 2自动触发'),
            sa.Column('expire_at', sa.DateTime, nullable=True, comment='解禁时间'),
            sa.Column('released_at', sa.DateTime, nullable=True, comment='实际解禁时间'),
            sa.Column('status', sa.Integer, server_default='1', comment='状态: 1生效 0已解禁'),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index('ix_blacklists_user_id', 'blacklists', ['user_id'])
        op.create_index('ix_blacklists_store_id', 'blacklists', ['store_id'])
        op.create_index('ix_blacklists_keyword', 'blacklists', ['keyword'])
        op.create_index('ix_blacklists_status', 'blacklists', ['status'])
    
    # ========== 确保 permissions 表存在 (来自 009) ==========
    if not table_exists('permissions'):
        op.create_table(
            'permissions',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('code', sa.String(100), unique=True, nullable=False, comment='权限码'),
            sa.Column('name', sa.String(100), nullable=False, comment='权限名称'),
            sa.Column('type', sa.String(20), nullable=False, comment='类型: menu/button'),
            sa.Column('parent_code', sa.String(100), comment='父级权限码'),
            sa.Column('icon', sa.String(50), comment='图标'),
            sa.Column('sort', sa.Integer, default=0, comment='排序号'),
            sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, onupdate=sa.func.now()),
        )
        op.create_index('ix_permissions_code', 'permissions', ['code'])
        op.create_index('ix_permissions_parent_code', 'permissions', ['parent_code'])
    
    # ========== 确保缺失的列存在 ==========
    # patients 表的列 (来自 006)
    patients_columns = [
        ('card_no', sa.String(50), None, '就诊卡编号'),
        ('province', sa.String(50), None, '省'),
        ('city', sa.String(50), None, '市'),
        ('district', sa.String(50), None, '区'),
        ('street', sa.String(100), None, '街道/社区'),
        ('id_card_type', sa.Integer, '1', '证件类型'),
        ('ethnicity', sa.String(20), '汉族', '民族'),
        ('address', sa.String(255), None, '详细地址'),
        ('source', sa.Integer, '1', '来源'),
        ('total_consumption', sa.Numeric(10, 2), '0', '累计消费'),
    ]
    
    if table_exists('patients'):
        for col_name, col_type, default, comment in patients_columns:
            if not column_exists('patients', col_name):
                if default is not None:
                    op.add_column('patients', sa.Column(col_name, col_type, server_default=default, comment=comment))
                else:
                    op.add_column('patients', sa.Column(col_name, col_type, nullable=True, comment=comment))
        
        if not index_exists('patients', 'ix_patients_card_no'):
            try:
                op.create_index('ix_patients_card_no', 'patients', ['card_no'], unique=True)
            except:
                pass
    
    # users 表的积分字段 (来自 006)
    if table_exists('users') and not column_exists('users', 'points'):
        op.add_column('users', sa.Column('points', sa.Integer, server_default='0', comment='当前积分'))
    
    # schedules 表的扩展字段 (来自 007_schedule_template)
    if table_exists('schedules'):
        if not column_exists('schedules', 'store_id'):
            op.add_column('schedules', sa.Column('store_id', sa.String(36), nullable=True, comment='门店ID'))
            try:
                op.create_foreign_key('fk_schedules_store_id', 'schedules', 'stores', ['store_id'], ['id'])
            except:
                pass
            try:
                op.create_index('ix_schedules_store_id', 'schedules', ['store_id'])
            except:
                pass
        
        if not column_exists('schedules', 'appointment_type'):
            op.add_column('schedules', sa.Column('appointment_type', sa.String(20), server_default='normal', comment='预约类型'))
        
        if not column_exists('schedules', 'template_id'):
            op.add_column('schedules', sa.Column('template_id', sa.String(36), nullable=True, comment='来源模板ID'))
            try:
                op.create_foreign_key('fk_schedules_template_id', 'schedules', 'schedule_templates', ['template_id'], ['id'])
            except:
                pass
            try:
                op.create_index('ix_schedules_template_id', 'schedules', ['template_id'])
            except:
                pass
    
    # ========== appointments 表的提醒字段 ==========
    if table_exists('appointments'):
        if not column_exists('appointments', 'reminder_sent'):
            op.add_column('appointments', sa.Column('reminder_sent', sa.Integer, server_default='0', comment='是否已发送提醒: 0否 1是'))
        
        if not column_exists('appointments', 'reminder_sent_at'):
            op.add_column('appointments', sa.Column('reminder_sent_at', sa.DateTime, nullable=True, comment='提醒发送时间'))
        
        # 创建提醒索引
        if not index_exists('appointments', 'idx_appointments_reminder'):
            try:
                op.create_index('idx_appointments_reminder', 'appointments', ['status', 'reminder_sent', 'schedule_id'])
            except:
                pass


def downgrade() -> None:
    """
    降级不删除任何表或列，因为这是一个合并迁移
    """
    pass

