"""Create schedule_holidays table for conflict detection

Revision ID: 095_create_schedule_holidays
Revises: 094_enhance_schedule_suspensions
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa


revision = '095_create_schedule_holidays'
down_revision = '094_enhance_schedule_suspensions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'schedule_holidays',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True, comment='租户ID'),
        sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=True, comment='门店ID，NULL表示全租户生效'),
        sa.Column('holiday_date', sa.Date(), nullable=False, index=True, comment='节假日日期'),
        sa.Column('name', sa.String(100), nullable=False, comment='节日名称'),
        sa.Column(
            'holiday_type', sa.String(20), nullable=False, server_default='legal',
            comment='类型: legal/hospital/makeup_workday',
        ),
        sa.Column(
            'allow_schedule', sa.Boolean(), nullable=False, server_default='false',
            comment='是否允许排班',
        ),
        sa.Column('status', sa.Integer(), server_default='1', comment='状态: 0已取消 1生效中'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), comment='更新时间'),
        sa.Column('created_by', sa.String(36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(36), nullable=True, comment='更新人ID'),
    )

    # 复合索引：租户+门店+日期（冲突检测主查询路径）
    op.create_index(
        'ix_schedule_holidays_tenant_store_date',
        'schedule_holidays',
        ['tenant_id', 'store_id', 'holiday_date'],
    )


def downgrade() -> None:
    op.drop_index('ix_schedule_holidays_tenant_store_date', table_name='schedule_holidays')
    op.drop_table('schedule_holidays')
