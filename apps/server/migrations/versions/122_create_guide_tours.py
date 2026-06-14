"""创建操作指引表

Revision ID: 122
Revises: 121
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision = '122'
down_revision = '121'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # guide_tours 表
    op.create_table(
        'guide_tours',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('code', sa.String(100), unique=True, nullable=False, index=True, comment='唯一标识'),
        sa.Column('title', JSONB, nullable=False, comment='多语言标题 {zh, en}'),
        sa.Column('description', JSONB, nullable=True, comment='多语言描述 {zh, en}'),
        sa.Column('steps', JSONB, nullable=False, server_default='[]', comment='步骤数组'),
        sa.Column('status', sa.Integer, nullable=False, server_default='0', comment='0=草稿, 1=已发布'),
        sa.Column('sort_order', sa.Integer, server_default='0', comment='排序'),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True, comment='NULL=全局指引'),
        sa.Column('created_by', sa.String(36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(36), nullable=True, comment='更新人ID'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), comment='更新时间'),
    )

    # guide_tour_progress 表
    op.create_table(
        'guide_tour_progress',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tour_id', sa.String(36), sa.ForeignKey('guide_tours.id', ondelete='CASCADE'), nullable=False, index=True, comment='指引ID'),
        sa.Column('admin_id', sa.String(36), sa.ForeignKey('admins.id'), nullable=False, index=True, comment='管理员ID'),
        sa.Column('current_step', sa.Integer, server_default='0', comment='当前步骤索引'),
        sa.Column('status', sa.Integer, server_default='0', comment='0=进行中, 1=已完成, 2=跳过'),
        sa.UniqueConstraint('tour_id', 'admin_id', name='uq_guide_tour_progress'),
    )


def downgrade() -> None:
    op.drop_table('guide_tour_progress')
    op.drop_table('guide_tours')
