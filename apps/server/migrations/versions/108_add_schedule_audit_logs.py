"""add schedule_audit_logs table

Revision ID: 108
Revises: 107
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = '108'
down_revision = '107'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'schedule_audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('schedule_id', sa.String(36), nullable=True, index=True, comment='排班ID（批量操作可为空）'),
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        sa.Column('action', sa.String(50), nullable=False, comment='操作类型: publish/suspend/resume/delete/withdraw/drag/copy'),
        sa.Column('operator_id', sa.String(36), nullable=True),
        sa.Column('snapshot_before', sa.Text, nullable=True, comment='操作前排班快照 JSON'),
        sa.Column('snapshot_after', sa.Text, nullable=True, comment='操作后排班快照 JSON'),
        sa.Column('changes', sa.Text, nullable=True, comment='字段级变更差异 JSON'),
        sa.Column('created_at', sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table('schedule_audit_logs')
