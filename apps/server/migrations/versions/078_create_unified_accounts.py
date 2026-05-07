"""创建统一账号体系 — accounts 主表 + 扩展表

Revision ID: 078_create_unified_accounts
Revises: 077_add_role_type_is_default
Create Date: 2026-05-06

变更内容：
  - 创建 accounts          统一账号主表
  - 创建 account_admins    管理员扩展表
  - 创建 account_doctors   医生扩展表
  - 创建 account_users     用户扩展表
  - 创建 account_admin_stores  管理员-门店关联表
  - 从 admins / doctors / users 三个旧表迁移数据到新表

注意：不删除旧表，业务代码渐进式切换。
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from datetime import datetime

revision = '078_create_unified_accounts'
down_revision = '077_add_role_type_is_default'
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# 辅助：旧表结构定义（用于数据迁移）
# ---------------------------------------------------------------------------
admins_t = table(
    'admins',
    column('id', sa.String),
    column('tenant_id', sa.String),
    column('username', sa.String),
    column('password_hash', sa.String),
    column('name', sa.String),
    column('phone', sa.String),
    column('email', sa.String),
    column('avatar', sa.String),
    column('role_id', sa.String),
    column('current_store_id', sa.String),
    column('status', sa.Integer),
    column('last_login_at', sa.DateTime),
    column('last_login_ip', sa.String),
    column('created_at', sa.DateTime),
    column('updated_at', sa.DateTime),
    column('created_by', sa.String),
    column('updated_by', sa.String),
)

doctors_t = table(
    'doctors',
    column('id', sa.String),
    column('tenant_id', sa.String),
    column('store_id', sa.String),
    column('department_id', sa.String),
    column('name', sa.String),
    column('username', sa.String),
    column('phone', sa.String),
    column('password_hash', sa.String),
    column('gender', sa.Integer),
    column('avatar', sa.String),
    column('banner', sa.String),
    column('title', sa.String),
    column('years_of_experience', sa.Integer),
    column('education', sa.String),
    column('graduate_school', sa.String),
    column('license_number', sa.String),
    column('license_image', sa.String),
    column('honors', sa.Text),
    column('schedule_desc', sa.String),
    column('max_daily_appointments', sa.Integer),
    column('online_consult_enabled', sa.Integer),
    column('online_consult_fee', sa.Numeric),
    column('page_style', sa.Integer),
    column('promo_video', sa.String),
    column('tags', sa.String),
    column('specialty', sa.Text),
    column('introduction', sa.Text),
    column('is_recommended', sa.Integer),
    column('sort_order', sa.Integer),
    column('status', sa.Integer),
    column('last_login_at', sa.DateTime),
    column('last_login_ip', sa.String),
    column('use_fee_template', sa.Integer),
    column('deleted_at', sa.DateTime),
    column('created_at', sa.DateTime),
    column('updated_at', sa.DateTime),
    column('created_by', sa.String),
    column('updated_by', sa.String),
)

users_t = table(
    'users',
    column('id', sa.String),
    column('tenant_id', sa.String),
    column('phone', sa.String),
    column('password_hash', sa.String),
    column('nickname', sa.String),
    column('avatar', sa.String),
    column('gender', sa.Integer),
    column('openid', sa.String),
    column('status', sa.Integer),
    column('points', sa.Integer),
    column('unionid', sa.String),
    column('wechat_nickname', sa.String),
    column('wechat_avatar', sa.String),
    column('wechat_synced_at', sa.DateTime),
    column('created_at', sa.DateTime),
    column('updated_at', sa.DateTime),
    column('created_by', sa.String),
    column('updated_by', sa.String),
)


def upgrade() -> None:
    # ===================================================================
    # 1. 创建 accounts 主表
    # ===================================================================
    op.create_table(
        'accounts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36),
                  sa.ForeignKey('tenants.id'), nullable=True, index=True,
                  comment='租户ID（NULL表示平台账号）'),
        sa.Column('phone', sa.String(20), index=True, comment='手机号'),
        sa.Column('username', sa.String(50), index=True, comment='用户名/登录账号'),
        sa.Column('password_hash', sa.String(255), comment='密码哈希'),
        sa.Column('nickname', sa.String(50), comment='昵称'),
        sa.Column('name', sa.String(50), comment='真实姓名'),
        sa.Column('avatar', sa.String(255), comment='头像URL'),
        sa.Column('gender', sa.Integer, server_default='0', comment='性别 0未知 1男 2女'),
        sa.Column('status', sa.Integer, server_default='1', comment='状态 0禁用 1正常'),
        sa.Column('last_login_at', sa.DateTime, comment='最后登录时间'),
        sa.Column('last_login_ip', sa.String(50), comment='最后登录IP'),
        sa.Column('created_at', sa.DateTime, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime, comment='更新时间'),
        sa.Column('created_by', sa.String(36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(36), nullable=True, comment='更新人ID'),
        sa.UniqueConstraint('tenant_id', 'phone', name='uq_accounts_tenant_phone'),
        sa.UniqueConstraint('tenant_id', 'username', name='uq_accounts_tenant_username'),
        comment='统一账号主表',
    )

    # ===================================================================
    # 2. 创建 account_admin_stores 关联表
    # ===================================================================
    op.create_table(
        'account_admin_stores',
        sa.Column('account_id', sa.String(36),
                  sa.ForeignKey('accounts.id', ondelete='CASCADE'),
                  primary_key=True, comment='账号ID'),
        sa.Column('store_id', sa.String(36),
                  sa.ForeignKey('stores.id', ondelete='CASCADE'),
                  primary_key=True, comment='门店ID'),
        sa.Column('is_manager', sa.Integer, server_default='0',
                  comment='是否为该门店管理员: 0否 1是'),
        sa.Column('created_at', sa.DateTime, comment='创建时间'),
    )

    # ===================================================================
    # 3. 创建 account_admins 扩展表
    # ===================================================================
    op.create_table(
        'account_admins',
        sa.Column('account_id', sa.String(36),
                  sa.ForeignKey('accounts.id', ondelete='CASCADE'),
                  primary_key=True),
        sa.Column('role_id', sa.String(36),
                  sa.ForeignKey('roles.id'), comment='角色ID'),
        sa.Column('current_store_id', sa.String(36),
                  sa.ForeignKey('stores.id'), nullable=True,
                  comment='当前选中门店ID'),
        sa.Column('email', sa.String(100), comment='邮箱'),
        sa.Column('created_at', sa.DateTime, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime, comment='更新时间'),
        sa.Column('created_by', sa.String(36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(36), nullable=True, comment='更新人ID'),
        comment='管理员扩展表',
    )

    # ===================================================================
    # 4. 创建 account_doctors 扩展表
    # ===================================================================
    op.create_table(
        'account_doctors',
        sa.Column('account_id', sa.String(36),
                  sa.ForeignKey('accounts.id', ondelete='CASCADE'),
                  primary_key=True),
        sa.Column('store_id', sa.String(36),
                  sa.ForeignKey('stores.id'), comment='所属门店ID'),
        sa.Column('department_id', sa.String(36),
                  sa.ForeignKey('departments.id'), nullable=False,
                  comment='所属科室ID'),
        # 基础信息（医生特有）
        sa.Column('banner', sa.String(255), comment='医生banner图URL'),
        sa.Column('title', sa.String(50), comment='职称'),
        sa.Column('years_of_experience', sa.Integer, server_default='0',
                  comment='医龄(年)'),
        # 资质信息
        sa.Column('education', sa.String(50), comment='学历'),
        sa.Column('graduate_school', sa.String(100), comment='毕业院校'),
        sa.Column('license_number', sa.String(100), comment='执业证书编号'),
        sa.Column('license_image', sa.String(255), comment='执业证书图片URL'),
        sa.Column('honors', sa.Text, comment='所获荣誉'),
        # 坐诊设置
        sa.Column('schedule_desc', sa.String(255), comment='坐诊时间说明'),
        sa.Column('max_daily_appointments', sa.Integer, server_default='0',
                  comment='每日最大接诊量,0表示不限制'),
        sa.Column('online_consult_enabled', sa.Integer, server_default='0',
                  comment='是否支持在线问诊 0否 1是'),
        sa.Column('online_consult_fee', sa.Numeric(10, 2), server_default='0',
                  comment='在线问诊费用'),
        # 展示设置
        sa.Column('page_style', sa.Integer, server_default='1',
                  comment='页面风格 1/2/3'),
        sa.Column('promo_video', sa.String(255), comment='宣传视频URL'),
        sa.Column('tags', sa.String(255), comment='标签,逗号分隔'),
        sa.Column('specialty', sa.Text, comment='擅长'),
        sa.Column('introduction', sa.Text, comment='简介'),
        # 其他设置
        sa.Column('is_recommended', sa.Integer, server_default='0',
                  comment='是否推荐 0否 1是'),
        sa.Column('sort_order', sa.Integer, server_default='0', comment='排序'),
        # 诊费设置
        sa.Column('use_fee_template', sa.Integer, server_default='0',
                  comment='是否使用诊费模板 0否 1是'),
        # 软删除
        sa.Column('deleted_at', sa.DateTime, nullable=True, comment='软删除时间'),
        # 审计字段
        sa.Column('created_at', sa.DateTime, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime, comment='更新时间'),
        sa.Column('created_by', sa.String(36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(36), nullable=True, comment='更新人ID'),
        comment='医生扩展表',
    )

    # ===================================================================
    # 5. 创建 account_users 扩展表
    # ===================================================================
    op.create_table(
        'account_users',
        sa.Column('account_id', sa.String(36),
                  sa.ForeignKey('accounts.id', ondelete='CASCADE'),
                  primary_key=True),
        # 冗余 tenant_id，用于唯一约束
        sa.Column('tenant_id', sa.String(36),
                  sa.ForeignKey('tenants.id'), nullable=True, index=True,
                  comment='租户ID（冗余，与 accounts.tenant_id 同步）'),
        # 微信相关
        sa.Column('openid', sa.String(100), index=True, comment='微信openid'),
        sa.Column('unionid', sa.String(100), index=True, nullable=True,
                  comment='微信开放平台统一ID'),
        sa.Column('wechat_nickname', sa.String(50), nullable=True,
                  comment='微信原始昵称'),
        sa.Column('wechat_avatar', sa.String(500), nullable=True,
                  comment='微信原始头像URL'),
        sa.Column('wechat_synced_at', sa.DateTime, nullable=True,
                  comment='最后同步微信信息时间'),
        # 积分
        sa.Column('points', sa.Integer, server_default='0', comment='当前积分'),
        # 审计字段
        sa.Column('created_at', sa.DateTime, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime, comment='更新时间'),
        sa.Column('created_by', sa.String(36), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.String(36), nullable=True, comment='更新人ID'),
        sa.UniqueConstraint('tenant_id', 'openid', name='uq_account_users_tenant_openid'),
        sa.UniqueConstraint('tenant_id', 'unionid', name='uq_account_users_tenant_unionid'),
        comment='用户扩展表',
    )

    # ===================================================================
    # 6. 数据迁移：从旧表迁移到新表
    # ===================================================================

    # 6a. 迁移 admins -> accounts + account_admins
    # 管理员没有 nickname，name 放入 accounts.name
    op.execute("""
        INSERT INTO accounts (id, tenant_id, phone, username, password_hash,
                              nickname, name, avatar, gender, status,
                              last_login_at, last_login_ip,
                              created_at, updated_at, created_by, updated_by)
        SELECT id, tenant_id, phone, username, password_hash,
               NULL, name, avatar, 0, status,
               last_login_at, last_login_ip,
               created_at, updated_at, created_by, updated_by
        FROM admins
    """)

    op.execute("""
        INSERT INTO account_admins (account_id, role_id, current_store_id, email,
                                    created_at, updated_at, created_by, updated_by)
        SELECT id, role_id, current_store_id, email,
               created_at, updated_at, created_by, updated_by
        FROM admins
    """)

    # 6b. 迁移 doctors -> accounts + account_doctors
    # 医生没有 nickname，name 放入 accounts.name
    op.execute("""
        INSERT INTO accounts (id, tenant_id, phone, username, password_hash,
                              nickname, name, avatar, gender, status,
                              last_login_at, last_login_ip,
                              created_at, updated_at, created_by, updated_by)
        SELECT id, tenant_id, phone, username, password_hash,
               NULL, name, avatar, gender, status,
               last_login_at, last_login_ip,
               created_at, updated_at, created_by, updated_by
        FROM doctors
    """)

    op.execute("""
        INSERT INTO account_doctors (
            account_id, store_id, department_id,
            banner, title, years_of_experience,
            education, graduate_school, license_number, license_image, honors,
            schedule_desc, max_daily_appointments,
            online_consult_enabled, online_consult_fee,
            page_style, promo_video, tags, specialty, introduction,
            is_recommended, sort_order,
            use_fee_template, deleted_at,
            created_at, updated_at, created_by, updated_by
        )
        SELECT
            id, store_id, department_id,
            banner, title, years_of_experience,
            education, graduate_school, license_number, license_image, honors,
            schedule_desc, max_daily_appointments,
            online_consult_enabled, online_consult_fee,
            page_style, promo_video, tags, specialty, introduction,
            is_recommended, sort_order,
            use_fee_template, deleted_at,
            created_at, updated_at, created_by, updated_by
        FROM doctors
    """)

    # 6c. 迁移 users -> accounts + account_users
    # users 有 nickname 但没有 name/username/last_login_at/last_login_ip
    op.execute("""
        INSERT INTO accounts (id, tenant_id, phone, username, password_hash,
                              nickname, name, avatar, gender, status,
                              last_login_at, last_login_ip,
                              created_at, updated_at, created_by, updated_by)
        SELECT id, tenant_id, phone, NULL, password_hash,
               nickname, NULL, avatar, gender, status,
               NULL, NULL,
               created_at, updated_at, created_by, updated_by
        FROM users
    """)

    op.execute("""
        INSERT INTO account_users (
            account_id, tenant_id,
            openid, unionid, wechat_nickname, wechat_avatar, wechat_synced_at,
            points,
            created_at, updated_at, created_by, updated_by
        )
        SELECT
            id, tenant_id,
            openid, unionid, wechat_nickname, wechat_avatar, wechat_synced_at,
            points,
            created_at, updated_at, created_by, updated_by
        FROM users
    """)


def downgrade() -> None:
    """降级：删除新表（不恢复旧数据，旧表保留不动）"""
    # 按依赖关系逆序删除
    op.drop_table('account_users')
    op.drop_table('account_doctors')
    op.drop_table('account_admins')
    op.drop_table('account_admin_stores')
    op.drop_table('accounts')
