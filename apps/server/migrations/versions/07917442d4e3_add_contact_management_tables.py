"""add contact management tables

Revision ID: 07917442d4e3
Revises: 126_add_approval_condition_group_id
Create Date: 2026-06-25 17:49:14.036104

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '07917442d4e3'
down_revision = '126_add_approval_condition_group_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === 联系人主表 ===
    op.create_table('contacts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False, comment='租户ID'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='联系人姓名'),
        sa.Column('nickname', sa.String(length=50), nullable=True, comment='昵称'),
        sa.Column('avatar', sa.String(length=255), nullable=True, comment='头像URL'),
        sa.Column('gender', sa.Integer(), nullable=True, comment='性别 0未知 1男 2女'),
        sa.Column('phone', sa.String(length=20), nullable=True, comment='手机号'),
        sa.Column('email', sa.String(length=100), nullable=True, comment='邮箱'),
        sa.Column('contact_type', sa.String(length=20), nullable=False, comment='联系人类型: patient/doctor/admin/staff/external'),
        sa.Column('source_type', sa.String(length=20), nullable=True, comment='来源类型: admin/doctor/patient/manual_import'),
        sa.Column('source_id', sa.String(length=36), nullable=True, comment='来源记录ID'),
        sa.Column('account_id', sa.String(length=36), nullable=True, comment='关联账号ID'),
        sa.Column('department_id', sa.String(length=36), nullable=True, comment='所属科室ID'),
        sa.Column('store_id', sa.String(length=36), nullable=True, comment='所属门店ID'),
        sa.Column('position', sa.String(length=50), nullable=True, comment='职位/职称'),
        sa.Column('organization', sa.String(length=200), nullable=True, comment='所属机构（外部联系人用）'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('status', sa.Integer(), nullable=True, comment='状态 0禁用 1正常'),
        sa.Column('last_contact_at', sa.DateTime(), nullable=True, comment='最后联系时间'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='软删除时间'),
        sa.Column('created_by', sa.String(length=36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(length=36), nullable=True, comment='更新人ID'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        comment='联系人表'
    )
    op.create_index('ix_contacts_tenant_id', 'contacts', ['tenant_id'])
    op.create_index('ix_contacts_phone', 'contacts', ['phone'])
    op.create_index('ix_contacts_email', 'contacts', ['email'])
    op.create_index('ix_contacts_account_id', 'contacts', ['account_id'])

    # === 联系人分组表 ===
    op.create_table('contact_groups',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False, comment='租户ID'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='分组名称'),
        sa.Column('description', sa.String(length=500), nullable=True, comment='分组描述'),
        sa.Column('parent_id', sa.String(length=36), nullable=True, comment='父分组ID'),
        sa.Column('sort_order', sa.Integer(), nullable=True, comment='排序'),
        sa.Column('status', sa.Integer(), nullable=True, comment='状态 0禁用 1正常'),
        sa.Column('created_by', sa.String(length=36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(length=36), nullable=True, comment='更新人ID'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.ForeignKeyConstraint(['parent_id'], ['contact_groups.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        comment='联系人分组表'
    )
    op.create_index('ix_contact_groups_tenant_id', 'contact_groups', ['tenant_id'])

    # === 联系人标签表 ===
    op.create_table('contact_tags',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False, comment='租户ID'),
        sa.Column('name', sa.String(length=50), nullable=False, comment='标签名称'),
        sa.Column('color', sa.String(length=20), nullable=True, comment='标签颜色'),
        sa.Column('sort_order', sa.Integer(), nullable=True, comment='排序'),
        sa.Column('created_by', sa.String(length=36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(length=36), nullable=True, comment='更新人ID'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_contact_tag_tenant_name'),
        comment='联系人标签表'
    )
    op.create_index('ix_contact_tags_tenant_id', 'contact_tags', ['tenant_id'])

    # === 渠道账号配置表 ===
    op.create_table('channel_accounts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False, comment='租户ID'),
        sa.Column('store_id', sa.String(length=36), nullable=True, comment='门店ID（NULL=全局账号）'),
        sa.Column('channel_type', sa.String(length=20), nullable=False, comment='渠道类型: sms/email/wechat/webhook'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='账号名称'),
        sa.Column('config', sa.Text(), nullable=False, comment='渠道配置JSON（敏感字段加密存储）'),
        sa.Column('status', sa.Integer(), nullable=True, comment='状态 0禁用 1正常 2验证中'),
        sa.Column('is_default', sa.Integer(), nullable=True, comment='是否为该渠道默认账号'),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True, comment='最后同步/验证时间'),
        sa.Column('last_error', sa.Text(), nullable=True, comment='最后错误信息'),
        sa.Column('created_by', sa.String(length=36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(length=36), nullable=True, comment='更新人ID'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        comment='渠道账号配置表'
    )
    op.create_index('ix_channel_accounts_tenant_id', 'channel_accounts', ['tenant_id'])
    op.create_index('ix_channel_accounts_store_id', 'channel_accounts', ['store_id'])

    # === 联系人渠道信息表 ===
    op.create_table('contact_channels',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('contact_id', sa.String(length=36), nullable=False, comment='联系人ID'),
        sa.Column('channel_type', sa.String(length=20), nullable=False, comment='渠道类型: phone/email/wechat/sms'),
        sa.Column('channel_value', sa.String(length=200), nullable=False, comment='渠道标识值（手机号/邮箱/openid）'),
        sa.Column('is_primary', sa.Integer(), nullable=True, comment='是否主要渠道'),
        sa.Column('verified', sa.Integer(), nullable=True, comment='是否已验证'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('contact_id', 'channel_type', 'channel_value', name='uq_contact_channel_value'),
        comment='联系人渠道信息表'
    )
    op.create_index('ix_contact_channels_contact_id', 'contact_channels', ['contact_id'])

    # === 联系人-分组关联表 ===
    op.create_table('contact_group_members',
        sa.Column('contact_id', sa.String(length=36), nullable=False),
        sa.Column('group_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['group_id'], ['contact_groups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('contact_id', 'group_id')
    )

    # === 联系人-标签关联表 ===
    op.create_table('contact_tag_members',
        sa.Column('contact_id', sa.String(length=36), nullable=False),
        sa.Column('tag_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['contact_tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('contact_id', 'tag_id')
    )


def downgrade() -> None:
    op.drop_table('contact_tag_members')
    op.drop_table('contact_group_members')
    op.drop_index('ix_contact_channels_contact_id', table_name='contact_channels')
    op.drop_table('contact_channels')
    op.drop_index('ix_channel_accounts_store_id', table_name='channel_accounts')
    op.drop_index('ix_channel_accounts_tenant_id', table_name='channel_accounts')
    op.drop_table('channel_accounts')
    op.drop_index('ix_contact_tags_tenant_id', table_name='contact_tags')
    op.drop_table('contact_tags')
    op.drop_index('ix_contact_groups_tenant_id', table_name='contact_groups')
    op.drop_table('contact_groups')
    op.drop_index('ix_contacts_account_id', table_name='contacts')
    op.drop_index('ix_contacts_email', table_name='contacts')
    op.drop_index('ix_contacts_phone', table_name='contacts')
    op.drop_index('ix_contacts_tenant_id', table_name='contacts')
    op.drop_table('contacts')
