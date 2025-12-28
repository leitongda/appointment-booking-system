"""add audit fields (created_by, updated_by) to all tables

Revision ID: 024_add_audit_fields
Revises: 023_last_generated_at
Create Date: 2024-12-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '024_add_audit_fields'
down_revision = '023_last_generated_at'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    try:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


# 需要添加审计字段的所有表
TABLES_TO_UPDATE = [
    # 用户相关
    'users',
    'patients',
    # 管理员相关
    'permissions',
    'roles',
    'admins',
    # 业务核心
    'doctors',
    'departments',
    'schedules',
    'appointments',
    'medical_records',
    # 门店
    'stores',
    # 内容管理
    'news',
    'notices',
    'banners',
    # 消息
    'messages',
    'message_templates',
    # 反馈和请求
    'feedbacks',
    'leave_requests',
    # 诊费相关
    'consultation_fee_types',
    'consultation_fee_templates',
    'store_fee_templates',
    'doctor_consultation_fees',
    # 预约设置
    'doctor_booking_settings',
    # 积分
    'point_logs',
    # 排班相关
    'schedule_templates',
    'rest_days',
    'schedule_suspensions',
    'custom_schedules',
    # 黑名单
    'blacklists',
    # 邮件模板
    'email_templates',
    # 系统设置
    'system_settings',
]


def upgrade():
    """添加 created_by 和 updated_by 字段到所有业务表"""
    for table_name in TABLES_TO_UPDATE:
        if not table_exists(table_name):
            print(f"表 {table_name} 不存在，跳过")
            continue
        
        # 添加 created_by 字段
        if not column_exists(table_name, 'created_by'):
            op.add_column(
                table_name,
                sa.Column('created_by', sa.String(36), nullable=True, comment='创建人ID')
            )
            print(f"表 {table_name} 已添加 created_by 字段")
        else:
            print(f"表 {table_name} 已存在 created_by 字段，跳过")
        
        # 添加 updated_by 字段
        if not column_exists(table_name, 'updated_by'):
            op.add_column(
                table_name,
                sa.Column('updated_by', sa.String(36), nullable=True, comment='更新人ID')
            )
            print(f"表 {table_name} 已添加 updated_by 字段")
        else:
            print(f"表 {table_name} 已存在 updated_by 字段，跳过")


def downgrade():
    """删除 created_by 和 updated_by 字段"""
    for table_name in TABLES_TO_UPDATE:
        if not table_exists(table_name):
            continue
        
        if column_exists(table_name, 'created_by'):
            op.drop_column(table_name, 'created_by')
        
        if column_exists(table_name, 'updated_by'):
            op.drop_column(table_name, 'updated_by')

