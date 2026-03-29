"""Add tenant_id to messages, medical_records, leave_requests, and rest_days

Revision ID: 050_add_tenant_id_to_isolated_tables
Revises: 049_store_password_hash
Create Date: 2026-03-29

为租户隔离修复添加 tenant_id 字段到以下表：
- messages: 消息表
- medical_records: 病历表
- leave_requests: 停诊/调班申请表
- rest_days: 休息日设置表
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '050_add_tenant_id_to_isolated_tables'
down_revision = '049_store_password_hash'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # messages 表添加 tenant_id
    op.add_column(
        'messages',
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True, comment='租户ID')
    )

    # medical_records 表添加 tenant_id
    op.add_column(
        'medical_records',
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True, comment='租户ID')
    )

    # leave_requests 表添加 tenant_id
    op.add_column(
        'leave_requests',
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True, comment='租户ID')
    )

    # rest_days 表添加 tenant_id
    op.add_column(
        'rest_days',
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True, comment='租户ID')
    )


def downgrade() -> None:
    op.drop_column('rest_days', 'tenant_id')
    op.drop_column('leave_requests', 'tenant_id')
    op.drop_column('medical_records', 'tenant_id')
    op.drop_column('messages', 'tenant_id')
