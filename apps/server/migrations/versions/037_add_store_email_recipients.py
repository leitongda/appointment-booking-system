"""add store_email_recipients table

Revision ID: 037_store_email_recipients
Revises: 036_null_offsets
Create Date: 2026-02-06

新增门店邮件接收人表，用于配置各门店的邮件通知接收人及其订阅的事件类型。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '037_store_email_recipients'
down_revision = '036_null_offsets'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'store_email_recipients',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=False, index=True, comment='门店ID'),
        sa.Column('name', sa.String(50), nullable=False, comment='接收人姓名'),
        sa.Column('email', sa.String(100), nullable=False, comment='邮箱地址'),
        sa.Column('event_types', sa.Text(), nullable=True, comment='订阅事件类型(JSON数组)'),
        sa.Column('status', sa.Integer(), nullable=True, default=1, comment='状态: 0-禁用 1-启用'),
        # 审计字段（来自 AuditMixin）
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('store_email_recipients')
