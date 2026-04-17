"""Add refund_records table

Revision ID: 053_add_refund_records_table
Revises: 052_add_payment_and_refund_fields
Create Date: 2026-04-10

新建退款记录表，支持退款幂等、退款审计、防重复退款。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '053_add_refund_records_table'
down_revision = '052_add_payment_and_refund_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'refund_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=False, index=True, comment='租户ID'),
        sa.Column('appointment_id', sa.String(36), sa.ForeignKey('appointments.id'), nullable=False, index=True, comment='预约ID'),
        sa.Column('payment_profile_id', sa.String(36), sa.ForeignKey('payment_profiles.id'), nullable=True, index=True, comment='支付配置ID(快照)'),
        sa.Column('refund_no', sa.String(64), nullable=False, unique=True, comment='退款单号(幂等键)'),
        sa.Column('out_trade_no', sa.String(100), nullable=True, comment='原支付商户订单号'),
        sa.Column('wx_transaction_id', sa.String(100), nullable=True, comment='原支付微信交易号'),
        sa.Column('refund_amount', sa.Numeric(10, 2), nullable=False, comment='本次退款金额'),
        sa.Column('original_amount', sa.Numeric(10, 2), nullable=False, comment='原支付金额(快照)'),
        sa.Column('refund_reason', sa.String(500), nullable=True, comment='退款原因'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending', comment='退款状态: pending/processing/success/failed'),
        sa.Column('wx_refund_id', sa.String(100), nullable=True, comment='微信退款单号'),
        sa.Column('callback_raw', sa.Text(), nullable=True, comment='微信退款回调原始数据'),
        sa.Column('callback_at', sa.DateTime(), nullable=True, comment='回调接收时间'),
        sa.Column('failed_reason', sa.String(500), nullable=True, comment='退款失败原因'),
        sa.Column('mch_id', sa.String(100), nullable=True, comment='退款使用的商户号(快照)'),
        sa.Column('sub_mchid', sa.String(100), nullable=True, comment='退款使用的子商户号(快照)'),
        # AuditMixin fields
        sa.Column('created_by', sa.String(36), nullable=True, comment='创建人'),
        sa.Column('updated_by', sa.String(36), nullable=True, comment='更新人'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), comment='更新时间'),
        sa.UniqueConstraint('appointment_id', 'refund_no', name='uq_refund_records_appointment_refund_no'),
        comment='退款记录表',
    )


def downgrade() -> None:
    op.drop_table('refund_records')
