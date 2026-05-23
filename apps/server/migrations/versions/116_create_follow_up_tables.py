"""create follow-up tables

Revision ID: 116
Revises: 115
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '116'
down_revision = '115'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 随访计划模板
    op.create_table(
        'follow_up_plans',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('department_id', sa.String(36), sa.ForeignKey('departments.id'), nullable=True, index=True),
        sa.Column('diagnosis_code', sa.String(50), nullable=True, index=True),
        sa.Column('diagnosis_name', sa.String(200), nullable=True),
        sa.Column('status', sa.Integer(), server_default='1'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, index=True),
        sa.Column('created_by', sa.String(36)),
        sa.Column('updated_by', sa.String(36)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # 随访计划步骤
    op.create_table(
        'follow_up_plan_steps',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('plan_id', sa.String(36), sa.ForeignKey('follow_up_plans.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('days_after_visit', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # 随访任务
    op.create_table(
        'follow_up_tasks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True),
        sa.Column('task_no', sa.String(50), unique=True, nullable=False),
        sa.Column('patient_id', sa.String(36), sa.ForeignKey('patients.id'), nullable=False, index=True),
        sa.Column('doctor_id', sa.String(36), sa.ForeignKey('doctors.id'), nullable=False, index=True),
        sa.Column('department_id', sa.String(36), sa.ForeignKey('departments.id'), nullable=False, index=True),
        sa.Column('appointment_id', sa.String(36), sa.ForeignKey('appointments.id'), nullable=True, index=True),
        sa.Column('medical_record_id', sa.String(36), sa.ForeignKey('medical_records.id'), nullable=True, index=True),
        sa.Column('plan_id', sa.String(36), sa.ForeignKey('follow_up_plans.id'), nullable=True, index=True),
        sa.Column('plan_step_id', sa.String(36), sa.ForeignKey('follow_up_plan_steps.id'), nullable=True),
        sa.Column('step_order', sa.Integer(), nullable=True),
        sa.Column('scheduled_date', sa.Date(), nullable=False, index=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending', index=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('completed_by', sa.String(36), nullable=True),
        sa.Column('skip_reason', sa.String(500), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, index=True),
        sa.Column('created_by', sa.String(36)),
        sa.Column('updated_by', sa.String(36)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_tasks_doctor_status_date', 'follow_up_tasks', ['doctor_id', 'status', 'scheduled_date'])

    # 随访记录
    op.create_table(
        'follow_up_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True),
        sa.Column('task_id', sa.String(36), sa.ForeignKey('follow_up_tasks.id'), nullable=True, index=True),
        sa.Column('patient_id', sa.String(36), sa.ForeignKey('patients.id'), nullable=False, index=True),
        sa.Column('doctor_id', sa.String(36), sa.ForeignKey('doctors.id'), nullable=False, index=True),
        sa.Column('appointment_id', sa.String(36), sa.ForeignKey('appointments.id'), nullable=True, index=True),
        sa.Column('medical_record_id', sa.String(36), sa.ForeignKey('medical_records.id'), nullable=True, index=True),
        sa.Column('follow_up_date', sa.DateTime(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('patient_condition', sa.String(20), nullable=True),
        sa.Column('next_action', sa.Text(), nullable=True),
        sa.Column('next_follow_up_date', sa.Date(), nullable=True),
        sa.Column('attachments', sa.Text(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, index=True),
        sa.Column('created_by', sa.String(36)),
        sa.Column('updated_by', sa.String(36)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('follow_up_records')
    op.drop_index('idx_tasks_doctor_status_date', table_name='follow_up_tasks')
    op.drop_table('follow_up_tasks')
    op.drop_table('follow_up_plan_steps')
    op.drop_table('follow_up_plans')
