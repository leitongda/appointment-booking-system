"""create store_daily_metrics

Revision ID: 121
Revises: 349003eaa3ce
Create Date: 2026-06-13

平台经营看台 — 门店每日经营指标预聚合表。
由 Celery 定时任务每日聚合写入，看板直接读取。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '121'
down_revision = '349003eaa3ce'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'store_daily_metrics',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True, comment='租户ID（NULL=平台级门店）'),
        sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=False, index=True, comment='门店ID'),
        sa.Column('stat_date', sa.Date(), nullable=False, index=True, comment='统计日期（就诊日）'),
        sa.Column('appointment_count', sa.Integer(), server_default='0', comment='当日预约总数'),
        sa.Column('visit_count', sa.Integer(), server_default='0', comment='已到院数'),
        sa.Column('completed_count', sa.Integer(), server_default='0', comment='已完成数'),
        sa.Column('no_show_count', sa.Integer(), server_default='0', comment='爽约数'),
        sa.Column('cancelled_count', sa.Integer(), server_default='0', comment='取消/过期数'),
        sa.Column('new_patient_count', sa.Integer(), server_default='0', comment='当日新患者数'),
        sa.Column('revenue', sa.Numeric(12, 2), server_default='0', comment='当日营收（诊费累计，预聚合）'),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'store_id', 'stat_date', name='uq_store_daily_metrics'),
        comment='门店每日经营指标快照（平台经营看台预聚合表）',
    )
    op.create_index(
        'ix_store_daily_metrics_tenant_date',
        'store_daily_metrics',
        ['tenant_id', 'stat_date'],
    )


def downgrade() -> None:
    op.drop_index('ix_store_daily_metrics_tenant_date', table_name='store_daily_metrics')
    op.drop_table('store_daily_metrics')
