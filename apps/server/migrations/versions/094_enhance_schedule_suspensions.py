"""Enhance schedule_suspensions for patient disposition

Revision ID: 094_enhance_schedule_suspensions
Revises: 093_backfill_quota_fields
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa


revision = '094_enhance_schedule_suspensions'
down_revision = '093_backfill_quota_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 停诊类型
    op.add_column(
        'schedule_suspensions',
        sa.Column(
            'suspension_type',
            sa.String(20),
            nullable=False,
            server_default='temporary',
            comment='停诊类型: temporary/full_day/partial/batch/holiday',
        ),
    )

    # 处置方式
    op.add_column(
        'schedule_suspensions',
        sa.Column(
            'processing_method',
            sa.String(20),
            nullable=True,
            comment='处置方式: auto_refund/reschedule/change_date/manual',
        ),
    )

    # 处置状态
    op.add_column(
        'schedule_suspensions',
        sa.Column(
            'processing_status',
            sa.String(20),
            nullable=False,
            server_default='pending',
            comment='处置状态: pending/processing/completed/failed',
        ),
    )

    # 受影响预约数
    op.add_column(
        'schedule_suspensions',
        sa.Column(
            'affected_appointment_count',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='受影响预约数',
        ),
    )

    # 停诊原因
    op.add_column(
        'schedule_suspensions',
        sa.Column(
            'reason',
            sa.String(500),
            nullable=True,
            comment='停诊原因',
        ),
    )


def downgrade() -> None:
    op.drop_column('schedule_suspensions', 'reason')
    op.drop_column('schedule_suspensions', 'affected_appointment_count')
    op.drop_column('schedule_suspensions', 'processing_status')
    op.drop_column('schedule_suspensions', 'processing_method')
    op.drop_column('schedule_suspensions', 'suspension_type')
