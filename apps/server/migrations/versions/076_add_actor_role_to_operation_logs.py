"""add actor role fields to operation_logs

Revision ID: 076_add_actor_role
Revises: 075_add_tags_log_retention
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

revision = '076_add_actor_role'
down_revision = '075_add_tags_log_retention'
branch_labels = None
depends_on = None


# 定义操作日志表结构（用于数据迁移）
operation_logs = table(
    'operation_logs',
    column('id', sa.String),
    column('admin_id', sa.String),
    column('admin_name', sa.String),
    column('actor_id', sa.String),
    column('actor_name', sa.String),
    column('actor_role', sa.String),
)


def upgrade() -> None:
    # 添加新字段
    op.add_column(
        'operation_logs',
        sa.Column('actor_id', sa.String(36), nullable=True, comment='操作者ID')
    )
    op.add_column(
        'operation_logs',
        sa.Column('actor_name', sa.String(50), nullable=True, comment='操作者姓名')
    )
    op.add_column(
        'operation_logs',
        sa.Column('actor_role', sa.String(20), nullable=True, comment='操作者角色: admin/doctor/user')
    )

    # 数据回填：将旧数据迁移到新字段
    # 所有现有的 admin_id/admin_name 数据都视为 admin 角色
    op.execute("""
        UPDATE operation_logs
        SET actor_id = admin_id,
            actor_name = admin_name,
            actor_role = 'admin'
        WHERE admin_id IS NOT NULL
    """)

    # 添加索引以提高查询性能
    op.create_index(
        'ix_operation_logs_actor_role',
        'operation_logs',
        ['actor_role']
    )
    op.create_index(
        'ix_operation_logs_actor_id',
        'operation_logs',
        ['actor_id']
    )


def downgrade() -> None:
    # 删除索引
    op.drop_index('ix_operation_logs_actor_id', table_name='operation_logs')
    op.drop_index('ix_operation_logs_actor_role', table_name='operation_logs')

    # 删除新字段
    op.drop_column('operation_logs', 'actor_role')
    op.drop_column('operation_logs', 'actor_name')
    op.drop_column('operation_logs', 'actor_id')
