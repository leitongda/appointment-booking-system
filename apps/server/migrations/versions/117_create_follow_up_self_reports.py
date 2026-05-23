"""create follow-up self-reports table

Revision ID: 117
Revises: 116
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '117'
down_revision = '116'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'follow_up_self_reports',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True),
        # 关联
        sa.Column('task_id', sa.String(36), sa.ForeignKey('follow_up_tasks.id'), nullable=True, index=True),
        sa.Column('patient_id', sa.String(36), sa.ForeignKey('patients.id'), nullable=False, index=True),
        # 报告信息
        sa.Column('report_date', sa.DateTime(), nullable=False),
        # 体征数据
        sa.Column('systolic_bp', sa.Integer(), nullable=True),
        sa.Column('diastolic_bp', sa.Integer(), nullable=True),
        sa.Column('blood_glucose', sa.Numeric(5, 1), nullable=True),
        sa.Column('heart_rate', sa.Integer(), nullable=True),
        sa.Column('temperature', sa.Numeric(4, 1), nullable=True),
        # 症状与感受
        sa.Column('symptoms', sa.Text(), nullable=True),
        sa.Column('patient_condition', sa.String(20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('attachments', sa.Text(), nullable=True),
        # 审核
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by', sa.String(36), nullable=True),
        # 软删除 + 审计
        sa.Column('deleted_at', sa.DateTime(), nullable=True, index=True),
        sa.Column('created_by', sa.String(36)),
        sa.Column('updated_by', sa.String(36)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_self_reports_patient_date', 'follow_up_self_reports', ['patient_id', 'report_date'])


def downgrade() -> None:
    op.drop_index('idx_self_reports_patient_date', table_name='follow_up_self_reports')
    op.drop_table('follow_up_self_reports')
