"""add approval flow base tables

Revision ID: 109_add_approval_flow_tables
Revises: 108
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = '109_add_approval_flow_tables'
down_revision = '108'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 审批流定义表
    op.create_table(
        'approval_flow_definitions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('business_type', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('form_schema', sa.JSON, nullable=True),
        sa.Column('callback_config', sa.JSON, nullable=True),
        sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=True),
        sa.Column('snapshot_json', sa.JSON, nullable=True),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
    )
    op.create_index('idx_flow_def_tenant_biz', 'approval_flow_definitions', ['tenant_id', 'business_type'])

    # 2. 审批流节点表
    op.create_table(
        'approval_flow_nodes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('flow_def_id', sa.String(36), sa.ForeignKey('approval_flow_definitions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('node_key', sa.String(100), nullable=False),
        sa.Column('node_name', sa.String(200), nullable=False),
        sa.Column('node_type', sa.String(30), nullable=False),
        sa.Column('approval_mode', sa.String(20), nullable=True),
        sa.Column('assignee_type', sa.String(30), nullable=True),
        sa.Column('assignee_config', sa.JSON, nullable=True),
        sa.Column('timeout_hours', sa.Integer, nullable=True),
        sa.Column('timeout_action', sa.String(20), nullable=True),
        sa.Column('sort_order', sa.Integer, nullable=False, server_default='0'),
        sa.Column('position_x', sa.Float, nullable=True),
        sa.Column('position_y', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
        comment='审批流节点表',
    )

    # 3. 审批流条件规则表
    op.create_table(
        'approval_flow_conditions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('node_id', sa.String(36), sa.ForeignKey('approval_flow_nodes.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('flow_def_id', sa.String(36), sa.ForeignKey('approval_flow_definitions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('target_node_key', sa.String(100), nullable=False),
        sa.Column('field_name', sa.String(200), nullable=False),
        sa.Column('operator', sa.String(20), nullable=False),
        sa.Column('value', sa.Text, nullable=False),
        sa.Column('priority', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime, nullable=True),
        comment='审批流条件规则表',
    )

    # 4. 审批实例表
    op.create_table(
        'approval_instances',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('flow_def_id', sa.String(36), sa.ForeignKey('approval_flow_definitions.id'), nullable=False, index=True),
        sa.Column('business_type', sa.String(100), nullable=False),
        sa.Column('business_id', sa.String(36), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('form_data', sa.JSON, nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='pending'),
        sa.Column('current_node_key', sa.String(100), nullable=True),
        sa.Column('applicant_id', sa.String(36), nullable=False),
        sa.Column('applicant_name', sa.String(100), nullable=True),
        sa.Column('approved_at', sa.DateTime, nullable=True),
        sa.Column('rejected_at', sa.DateTime, nullable=True),
        sa.Column('cancelled_at', sa.DateTime, nullable=True),
        sa.Column('completed_reason', sa.String(50), nullable=True),
        sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=True),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
        comment='审批实例表',
    )
    op.create_index('idx_appr_inst_biz', 'approval_instances', ['business_type', 'business_id'])
    op.create_index('idx_appr_inst_applicant', 'approval_instances', ['applicant_id'])
    op.create_index('idx_appr_inst_status', 'approval_instances', ['status'])
    op.create_index('idx_appr_inst_store_status', 'approval_instances', ['store_id', 'status'])

    # 5. 审批记录表
    op.create_table(
        'approval_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('instance_id', sa.String(36), sa.ForeignKey('approval_instances.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('node_key', sa.String(100), nullable=False),
        sa.Column('node_name', sa.String(200), nullable=True),
        sa.Column('approver_id', sa.String(36), nullable=False),
        sa.Column('approver_name', sa.String(100), nullable=True),
        sa.Column('action', sa.String(30), nullable=False),
        sa.Column('comment', sa.Text, nullable=True),
        sa.Column('delegate_to', sa.String(36), nullable=True),
        sa.Column('attachments', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        comment='审批记录表',
    )
    op.create_index('idx_appr_rec_approver', 'approval_records', ['approver_id'])
    op.create_index('idx_appr_rec_instance_node', 'approval_records', ['instance_id', 'node_key'])


def downgrade() -> None:
    op.drop_table('approval_records')
    op.drop_table('approval_instances')
    op.drop_table('approval_flow_conditions')
    op.drop_table('approval_flow_nodes')
    op.drop_table('approval_flow_definitions')
