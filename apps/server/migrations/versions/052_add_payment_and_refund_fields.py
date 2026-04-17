"""Add payment amount, transaction ID and refund fields to appointments

Revision ID: 052_add_payment_and_refund_fields
Revises: 051_add_rule_set_presets_table
Create Date: 2026-04-10

为预约表添加支付金额、交易号和退款相关字段，为支付/退款流程提供数据基础。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '052_add_payment_and_refund_fields'
down_revision = '051_add_rule_set_presets_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('appointments', sa.Column('payment_amount', sa.Numeric(10, 2), nullable=True, comment='支付金额(快照)'))
    op.add_column('appointments', sa.Column('payment_transaction_id', sa.String(100), nullable=True, comment='微信支付交易号/外部订单号'))
    op.add_column('appointments', sa.Column('paid_at', sa.DateTime(), nullable=True, comment='支付完成时间'))
    op.add_column('appointments', sa.Column('refund_status', sa.String(20), nullable=True, comment='退款状态: none/partial_refunded/refunded'))
    op.add_column('appointments', sa.Column('refund_amount', sa.Numeric(10, 2), nullable=True, server_default='0', comment='累计退款金额'))


def downgrade() -> None:
    op.drop_column('appointments', 'refund_amount')
    op.drop_column('appointments', 'refund_status')
    op.drop_column('appointments', 'paid_at')
    op.drop_column('appointments', 'payment_transaction_id')
    op.drop_column('appointments', 'payment_amount')
