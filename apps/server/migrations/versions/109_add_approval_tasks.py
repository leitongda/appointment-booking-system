"""add approval_tasks table + snapshot_json field

Revision ID: 109
Revises: 108
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = '110'
down_revision = '109_add_approval_flow_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 新增 approval_tasks 表
    op.create_table(
        'approval_tasks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True),
        sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=True),
        sa.Column('instance_id', sa.String(36), sa.ForeignKey('approval_instances.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('node_key', sa.String(100), nullable=False, comment='节点 key'),
        sa.Column('node_name', sa.String(200), nullable=True, comment='节点名称'),
        sa.Column('task_type', sa.String(30), nullable=False, server_default='approval', comment='approval/cc'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending', comment='pending/completed/cancelled/transferred/expired'),
        sa.Column('assignee_id', sa.String(36), nullable=False, comment='审批人 ID'),
        sa.Column('assignee_name', sa.String(100), nullable=True, comment='审批人姓名'),
        sa.Column('candidate_user_ids', sa.JSON, nullable=True, comment='候选人 ID 列表'),
        sa.Column('assignee_snapshot', sa.JSON, nullable=True, comment='审批人解析快照'),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('completed_by', sa.String(36), nullable=True, comment='完成操作人'),
        sa.Column('timeout_at', sa.DateTime, nullable=True, comment='超时时间'),
        sa.Column('created_at', sa.DateTime, nullable=True),
        comment='审批任务表',
    )
    op.create_index('idx_appr_task_tenant_status', 'approval_tasks', ['tenant_id', 'status'])
    op.create_index('idx_appr_task_assignee_status', 'approval_tasks', ['assignee_id', 'status'])
    op.create_index('idx_appr_task_instance_node', 'approval_tasks', ['instance_id', 'node_key'])


def downgrade() -> None:
    op.drop_index('idx_appr_task_instance_node', table_name='approval_tasks')
    op.drop_index('idx_appr_task_assignee_status', table_name='approval_tasks')
    op.drop_index('idx_appr_task_tenant_status', table_name='approval_tasks')
    op.drop_table('approval_tasks')
