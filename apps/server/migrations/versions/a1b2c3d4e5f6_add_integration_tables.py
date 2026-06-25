"""add integration tables

第三方集成配置（钉钉/企业微信/飞书）：
- integrations: 租户级应用凭证与群机器人配置
- integration_bindings: 用户账号与第三方平台绑定关系

Revision ID: a1b2c3d4e5f6
Revises: 53189cfdc81a
Create Date: 2026-06-25 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '53189cfdc81a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- integrations: 第三方集成配置 ---
    op.create_table(
        'integrations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False, comment='租户ID'),
        sa.Column('provider', sa.String(length=20), nullable=False, comment='集成平台: dingtalk/wecom/feishu'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='集成名称（便于识别）'),
        sa.Column('app_id', sa.String(length=100), nullable=True, comment='应用ID: 钉钉AppKey / 企业微信CorpID / 飞书AppID'),
        sa.Column('app_secret_ref', sa.String(length=255), nullable=True, comment='应用Secret引用，例如 env:DINGTALK_APP_SECRET'),
        sa.Column('webhook_url', sa.String(length=500), nullable=True, comment='群机器人 Webhook 地址'),
        sa.Column('webhook_secret_ref', sa.String(length=255), nullable=True, comment='群机器人加签密钥引用'),
        sa.Column('extra_config', sa.JSON(), nullable=True, comment='平台扩展配置(JSON)'),
        sa.Column('status', sa.Integer(), nullable=True, comment='状态: 0-禁用 1-启用'),
        sa.Column('created_by', sa.String(length=36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(length=36), nullable=True, comment='更新人ID'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'provider', name='uq_integrations_tenant_provider'),
        comment='第三方集成配置表',
    )
    op.create_index('ix_integrations_tenant_id', 'integrations', ['tenant_id'])

    # --- integration_bindings: 第三方账号绑定 ---
    op.create_table(
        'integration_bindings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False, comment='租户ID'),
        sa.Column('user_id', sa.String(length=36), nullable=False, comment='本地用户ID'),
        sa.Column('user_type', sa.String(length=20), nullable=False, comment='用户类型: admin/doctor/user'),
        sa.Column('provider', sa.String(length=20), nullable=False, comment='集成平台: dingtalk/wecom/feishu'),
        sa.Column('external_id', sa.String(length=100), nullable=False, comment='平台用户ID: 钉钉userId / 企业微信userid / 飞书open_id'),
        sa.Column('union_id', sa.String(length=100), nullable=True, comment='跨应用unionId（钉钉/企业微信支持）'),
        sa.Column('name', sa.String(length=100), nullable=True, comment='平台侧昵称（同步用）'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'provider', 'external_id', name='uq_ib_tenant_provider_ext'),
        sa.UniqueConstraint('tenant_id', 'provider', 'user_id', name='uq_ib_tenant_provider_user'),
        comment='第三方账号绑定关系表',
    )
    op.create_index('ix_integration_bindings_tenant_id', 'integration_bindings', ['tenant_id'])
    op.create_index('ix_integration_bindings_user_id', 'integration_bindings', ['user_id'])

    # --- 扩展 notification_preferences：第三方平台渠道偏好开关 ---
    op.add_column('notification_preferences',
                  sa.Column('dingtalk_enabled', sa.Boolean(), nullable=True, comment='钉钉推送'))
    op.add_column('notification_preferences',
                  sa.Column('wecom_enabled', sa.Boolean(), nullable=True, comment='企业微信推送'))
    op.add_column('notification_preferences',
                  sa.Column('feishu_enabled', sa.Boolean(), nullable=True, comment='飞书推送'))
    # 已有用户默认启用
    op.execute("UPDATE notification_preferences SET dingtalk_enabled = TRUE, wecom_enabled = TRUE, feishu_enabled = TRUE")

    # --- 扩展 unified_templates：第三方平台模板字段 ---
    op.add_column('unified_templates',
                  sa.Column('dingtalk_msg_template', sa.JSON(), nullable=True, comment='钉钉工作通知消息体模板'))
    op.add_column('unified_templates',
                  sa.Column('wecom_msg_template', sa.JSON(), nullable=True, comment='企业微信应用消息模板'))
    op.add_column('unified_templates',
                  sa.Column('feishu_msg_template', sa.JSON(), nullable=True, comment='飞书消息模板'))
    op.add_column('unified_templates',
                  sa.Column('robot_msg_template', sa.Text(), nullable=True, comment='群机器人通用 markdown 模板（三平台共用）'))


def downgrade() -> None:
    # unified_templates 列
    op.drop_column('unified_templates', 'robot_msg_template')
    op.drop_column('unified_templates', 'feishu_msg_template')
    op.drop_column('unified_templates', 'wecom_msg_template')
    op.drop_column('unified_templates', 'dingtalk_msg_template')

    # notification_preferences 列
    op.drop_column('notification_preferences', 'feishu_enabled')
    op.drop_column('notification_preferences', 'wecom_enabled')
    op.drop_column('notification_preferences', 'dingtalk_enabled')

    # 绑定表
    op.drop_index('ix_integration_bindings_user_id', table_name='integration_bindings')
    op.drop_index('ix_integration_bindings_tenant_id', table_name='integration_bindings')
    op.drop_table('integration_bindings')
    op.drop_index('ix_integrations_tenant_id', table_name='integrations')
    op.drop_table('integrations')
