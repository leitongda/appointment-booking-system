"""Create extra_quota_requests table for add-on quota approval workflow

Revision ID: 097_add_extra_quota_requests
Revises: 096_add_notification_log_fallback_fields
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa


revision = '097_add_extra_quota_requests'
down_revision = '096_add_notification_log_fallback_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'extra_quota_requests',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=False, comment='租户ID'),
        sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=False, comment='门店ID'),
        sa.Column('schedule_id', sa.String(36), sa.ForeignKey('schedules.id'), nullable=False, comment='排班ID'),
        sa.Column('doctor_id', sa.String(36), sa.ForeignKey('doctors.id'), nullable=False, comment='医生ID'),
        sa.Column('schedule_date', sa.String(10), nullable=False, comment='排班日期 YYYY-MM-DD'),
        sa.Column('time_slot', sa.String(20), nullable=False, comment='时间段: morning/afternoon/evening'),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1', comment='加号数量'),
        sa.Column('quota_type', sa.String(20), nullable=False, server_default='normal', comment='加号类型: normal/special/green_channel'),
        sa.Column('open_to_public', sa.Integer(), server_default='1', comment='是否对外开放: 1=是 0=否'),
        sa.Column('patient_id', sa.String(36), nullable=True, comment='指定患者ID（特批加号时使用）'),
        sa.Column('reason', sa.Text(), nullable=True, comment='加号原因'),
        sa.Column('approval_status', sa.String(20), nullable=False, server_default='pending', comment='审批状态: pending/approved/rejected/cancelled'),
        sa.Column('applicant_id', sa.String(36), nullable=False, comment='申请人ID'),
        sa.Column('approver_id', sa.String(36), nullable=True, comment='审批人ID'),
        sa.Column('approval_remark', sa.Text(), nullable=True, comment='审批备注'),
        sa.Column('approved_at', sa.DateTime(), nullable=True, comment='审批时间'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.Column('created_by', sa.String(36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(36), nullable=True, comment='更新人ID'),
        comment='加号申请表',
    )

    # 单字段索引
    op.create_index('ix_extra_quota_requests_tenant_id', 'extra_quota_requests', ['tenant_id'])
    op.create_index('ix_extra_quota_requests_store_id', 'extra_quota_requests', ['store_id'])
    op.create_index('ix_extra_quota_requests_schedule_id', 'extra_quota_requests', ['schedule_id'])
    op.create_index('ix_extra_quota_requests_doctor_id', 'extra_quota_requests', ['doctor_id'])

    # 复合索引：租户 + 排班
    op.create_index(
        'ix_extra_quota_tenant_schedule',
        'extra_quota_requests',
        ['tenant_id', 'schedule_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_extra_quota_tenant_schedule', table_name='extra_quota_requests')
    op.drop_index('ix_extra_quota_requests_doctor_id', table_name='extra_quota_requests')
    op.drop_index('ix_extra_quota_requests_schedule_id', table_name='extra_quota_requests')
    op.drop_index('ix_extra_quota_requests_store_id', table_name='extra_quota_requests')
    op.drop_index('ix_extra_quota_requests_tenant_id', table_name='extra_quota_requests')
    op.drop_table('extra_quota_requests')
