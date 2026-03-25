"""add multi-tenant support

Revision ID: 039_tenant_support
Revises: 038_unify_gender
Create Date: 2026-03-23

多租户架构核心表：
- subscription_plans: 订阅计划表
- tenants: 租户表
- tenant_subscriptions: 租户订阅记录表
- tenant_usage_logs: 租户用量统计表

同时为 stores 和 admins 表添加 tenant_id 字段。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '039_tenant_support'
down_revision = '038_unify_doctor_gender_enum'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 创建订阅计划表
    op.create_table(
        'subscription_plans',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('plan_code', sa.String(50), unique=True, nullable=False, comment='计划编码'),
        sa.Column('name', sa.String(100), nullable=False, comment='计划名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='计划描述'),
        # 价格信息
        sa.Column('price_monthly', sa.Numeric(10, 2), default=0, comment='月付价格'),
        sa.Column('price_yearly', sa.Numeric(10, 2), default=0, comment='年付价格'),
        sa.Column('currency', sa.String(10), default='CNY', comment='货币单位'),
        # 配额限制
        sa.Column('max_stores', sa.Integer(), default=1, comment='最大门店数'),
        sa.Column('max_admins', sa.Integer(), default=5, comment='最大管理员数'),
        sa.Column('max_doctors', sa.Integer(), default=50, comment='最大医生数'),
        sa.Column('max_appointments_per_month', sa.Integer(), default=1000, comment='月预约上限'),
        sa.Column('max_storage_mb', sa.Integer(), default=1024, comment='存储空间上限(MB)'),
        # 功能配置
        sa.Column('features', sa.Text(), nullable=True, comment='功能开关配置(JSON)'),
        # 状态
        sa.Column('status', sa.Integer(), default=1, comment='状态: 0-禁用 1-启用'),
        sa.Column('sort_order', sa.Integer(), default=0, comment='排序'),
        sa.Column('is_default', sa.Boolean(), default=False, comment='是否为默认计划'),
        # 审计字段
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=True),
    )
    op.create_index('idx_subscription_plans_code', 'subscription_plans', ['plan_code'])
    op.create_index('idx_subscription_plans_status', 'subscription_plans', ['status'])

    # 2. 创建租户表
    op.create_table(
        'tenants',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_code', sa.String(50), unique=True, nullable=False, comment='租户标识'),
        sa.Column('name', sa.String(100), nullable=False, comment='租户名称'),
        sa.Column('status', sa.Integer(), default=1, comment='状态: 0-禁用 1-正常 2-欠费 3-试用'),
        # 订阅信息
        sa.Column('subscription_plan_id', sa.String(36), sa.ForeignKey('subscription_plans.id'), nullable=True, comment='订阅计划ID'),
        sa.Column('subscription_start_at', sa.DateTime(), nullable=True, comment='订阅开始时间'),
        sa.Column('subscription_end_at', sa.DateTime(), nullable=True, comment='订阅结束时间'),
        sa.Column('billing_cycle', sa.String(20), default='monthly', comment='计费周期'),
        # 配额限制（覆盖计划默认值）
        sa.Column('max_stores', sa.Integer(), nullable=True, comment='最大门店数'),
        sa.Column('max_admins', sa.Integer(), nullable=True, comment='最大管理员数'),
        sa.Column('max_doctors', sa.Integer(), nullable=True, comment='最大医生数'),
        sa.Column('max_appointments_per_month', sa.Integer(), nullable=True, comment='月预约上限'),
        # 功能配置
        sa.Column('features', sa.Text(), nullable=True, comment='功能开关(JSON)'),
        sa.Column('branding_config', sa.Text(), nullable=True, comment='品牌配置(JSON)'),
        # 联系信息
        sa.Column('contact_name', sa.String(100), nullable=True, comment='联系人姓名'),
        sa.Column('contact_phone', sa.String(20), nullable=True, comment='联系电话'),
        sa.Column('contact_email', sa.String(100), nullable=True, comment='联系邮箱'),
        sa.Column('address', sa.String(255), nullable=True, comment='详细地址'),
        # 域名配置
        sa.Column('custom_domain', sa.String(255), nullable=True, comment='自定义域名'),
        sa.Column('subdomain', sa.String(100), nullable=True, comment='子域名前缀'),
        # 审计字段
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=True),
    )
    op.create_index('idx_tenants_code', 'tenants', ['tenant_code'])
    op.create_index('idx_tenants_status', 'tenants', ['status'])
    op.create_index('idx_tenants_subscription_plan', 'tenants', ['subscription_plan_id'])

    # 3. 创建租户订阅记录表
    op.create_table(
        'tenant_subscriptions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=False, comment='租户ID'),
        sa.Column('plan_id', sa.String(36), sa.ForeignKey('subscription_plans.id'), nullable=False, comment='订阅计划ID'),
        # 订阅信息
        sa.Column('plan_code', sa.String(50), nullable=False, comment='计划编码快照'),
        sa.Column('plan_name', sa.String(100), nullable=False, comment='计划名称快照'),
        sa.Column('billing_cycle', sa.String(20), nullable=False, comment='计费周期'),
        # 时间范围
        sa.Column('start_at', sa.DateTime(), nullable=False, comment='开始时间'),
        sa.Column('end_at', sa.DateTime(), nullable=False, comment='结束时间'),
        # 金额信息
        sa.Column('amount', sa.Numeric(10, 2), nullable=True, comment='金额'),
        sa.Column('currency', sa.String(10), default='CNY', comment='货币单位'),
        sa.Column('discount_rate', sa.Numeric(5, 2), default=0, comment='折扣率(%)'),
        sa.Column('final_amount', sa.Numeric(10, 2), nullable=True, comment='最终金额'),
        # 支付状态
        sa.Column('payment_status', sa.String(20), default='pending', comment='支付状态'),
        sa.Column('payment_method', sa.String(50), nullable=True, comment='支付方式'),
        sa.Column('payment_transaction_id', sa.String(100), nullable=True, comment='支付交易ID'),
        sa.Column('paid_at', sa.DateTime(), nullable=True, comment='支付时间'),
        # 状态
        sa.Column('status', sa.Integer(), default=1, comment='状态'),
        sa.Column('auto_renew', sa.Boolean(), default=False, comment='是否自动续费'),
        # 审计字段
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=True),
    )
    op.create_index('idx_tenant_subscriptions_tenant', 'tenant_subscriptions', ['tenant_id'])
    op.create_index('idx_tenant_subscriptions_plan', 'tenant_subscriptions', ['plan_id'])
    op.create_index('idx_tenant_subscriptions_status', 'tenant_subscriptions', ['status'])

    # 4. 创建租户用量统计表
    op.create_table(
        'tenant_usage_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=False, comment='租户ID'),
        sa.Column('usage_date', sa.Date(), nullable=False, comment='统计日期'),
        # 预约统计
        sa.Column('appointment_count', sa.Integer(), default=0, comment='预约数'),
        sa.Column('appointment_completed_count', sa.Integer(), default=0, comment='完成预约数'),
        sa.Column('appointment_cancelled_count', sa.Integer(), default=0, comment='取消预约数'),
        # 用户统计
        sa.Column('new_user_count', sa.Integer(), default=0, comment='新用户数'),
        sa.Column('active_user_count', sa.Integer(), default=0, comment='活跃用户数'),
        # 医生统计
        sa.Column('active_doctor_count', sa.Integer(), default=0, comment='活跃医生数'),
        # 存储统计
        sa.Column('storage_used_mb', sa.Numeric(10, 2), default=0, comment='存储用量(MB)'),
        # 消息统计
        sa.Column('sms_sent_count', sa.Integer(), default=0, comment='短信发送数'),
        sa.Column('push_sent_count', sa.Integer(), default=0, comment='推送发送数'),
        # 创建时间
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
    )
    op.create_index('idx_tenant_usage_logs_tenant', 'tenant_usage_logs', ['tenant_id'])
    op.create_index('idx_tenant_usage_logs_date', 'tenant_usage_logs', ['usage_date'])
    # 创建唯一约束：每个租户每天一条记录
    op.create_unique_constraint('uq_tenant_usage_date', 'tenant_usage_logs', ['tenant_id', 'usage_date'])

    # 5. 为 stores 表添加 tenant_id 字段
    op.add_column('stores', sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, comment='租户ID'))
    op.create_index('idx_stores_tenant_id', 'stores', ['tenant_id'])

    # 6. 为 admins 表添加 tenant_id 字段
    op.add_column('admins', sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, comment='租户ID'))
    op.create_index('idx_admins_tenant_id', 'admins', ['tenant_id'])


def downgrade() -> None:
    # 删除 admins 表的 tenant_id
    op.drop_index('idx_admins_tenant_id', 'admins')
    op.drop_column('admins', 'tenant_id')

    # 删除 stores 表的 tenant_id
    op.drop_index('idx_stores_tenant_id', 'stores')
    op.drop_column('stores', 'tenant_id')

    # 删除租户用量统计表
    op.drop_constraint('uq_tenant_usage_date', 'tenant_usage_logs', type_='unique')
    op.drop_index('idx_tenant_usage_logs_date', 'tenant_usage_logs')
    op.drop_index('idx_tenant_usage_logs_tenant', 'tenant_usage_logs')
    op.drop_table('tenant_usage_logs')

    # 删除租户订阅记录表
    op.drop_index('idx_tenant_subscriptions_status', 'tenant_subscriptions')
    op.drop_index('idx_tenant_subscriptions_plan', 'tenant_subscriptions')
    op.drop_index('idx_tenant_subscriptions_tenant', 'tenant_subscriptions')
    op.drop_table('tenant_subscriptions')

    # 删除租户表
    op.drop_index('idx_tenants_subscription_plan', 'tenants')
    op.drop_index('idx_tenants_status', 'tenants')
    op.drop_index('idx_tenants_code', 'tenants')
    op.drop_table('tenants')

    # 删除订阅计划表
    op.drop_index('idx_subscription_plans_status', 'subscription_plans')
    op.drop_index('idx_subscription_plans_code', 'subscription_plans')
    op.drop_table('subscription_plans')
