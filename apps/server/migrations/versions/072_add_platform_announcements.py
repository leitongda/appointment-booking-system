"""add platform_announcements table

Revision ID: 072_add_platform_announcements
Revises: 071
Create Date: 2026-04-28
"""
from alembic import op
import sqlalchemy as sa


revision = '072_add_platform_announcements'
down_revision = '071_add_tenant_id_to_remaining_models'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'platform_announcements',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False, comment='公告标题'),
        sa.Column('content', sa.Text(), nullable=False, comment='公告内容'),
        sa.Column('target_type', sa.String(20), nullable=False, default='all', comment='目标类型: all-全部租户 specific-指定租户'),
        sa.Column('target_tenant_ids', sa.Text(), nullable=True, comment='目标租户ID列表(JSON)'),
        sa.Column('status', sa.String(20), nullable=False, default='draft', comment='状态: draft-草稿 published-已发布 revoked-已撤回'),
        sa.Column('priority', sa.Integer(), default=0, comment='优先级: 0-普通 1-重要 2-紧急'),
        sa.Column('publish_at', sa.DateTime(), nullable=True, comment='定时发布时间'),
        sa.Column('expire_at', sa.DateTime(), nullable=True, comment='过期时间'),
        sa.Column('publisher_id', sa.String(36), nullable=True, comment='发布人ID'),
        sa.Column('publisher_name', sa.String(50), nullable=True, comment='发布人名称'),
        sa.Column('read_count', sa.Integer(), default=0, comment='已读数量'),
        sa.Column('total_count', sa.Integer(), default=0, comment='目标租户总数'),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now(), comment='更新时间'),
        sa.Index('ix_platform_announcements_status', 'status'),
        sa.Index('ix_platform_announcements_publish_at', 'publish_at'),
        comment='平台公告表',
    )


def downgrade():
    op.drop_table('platform_announcements')
