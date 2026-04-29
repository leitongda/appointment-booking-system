"""add support_tickets table

Revision ID: 073_add_support_tickets
Revises: 072_add_platform_announcements
Create Date: 2026-04-28
"""
from alembic import op
import sqlalchemy as sa


revision = '073_add_support_tickets'
down_revision = '072_add_platform_announcements'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'support_tickets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True, comment='租户ID'),
        sa.Column('title', sa.String(200), nullable=False, comment='工单标题'),
        sa.Column('description', sa.Text(), nullable=False, comment='工单描述'),
        sa.Column('type', sa.String(20), nullable=False, default='other', comment='工单类型: suggestion/complaint/bug/other'),
        sa.Column('status', sa.String(20), nullable=False, default='pending', comment='状态: pending/processing/resolved/closed'),
        sa.Column('priority', sa.String(20), nullable=False, default='medium', comment='优先级: low/medium/high/urgent'),
        sa.Column('creator_id', sa.String(36), nullable=False, index=True, comment='创建人ID'),
        sa.Column('creator_type', sa.String(20), nullable=False, default='user', comment='创建人类型: user/admin'),
        sa.Column('assignee_id', sa.String(36), nullable=True, comment='处理人ID'),
        sa.Column('contact_info', sa.String(200), nullable=True, comment='联系方式'),
        sa.Column('attachments', sa.JSON(), nullable=True, comment='附件列表(JSON)'),
        sa.Column('resolution', sa.Text(), nullable=True, comment='解决方案/备注'),
        sa.Column('closed_at', sa.DateTime(), nullable=True, comment='关闭时间'),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now(), nullable=False, comment='更新时间'),
        sa.Index('ix_support_tickets_tenant_status', 'tenant_id', 'status'),
        sa.Index('ix_support_tickets_tenant_created', 'tenant_id', 'created_at'),
        comment='工单支持表',
    )


def downgrade():
    op.drop_table('support_tickets')
