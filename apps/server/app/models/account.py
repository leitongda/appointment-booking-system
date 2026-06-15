"""统一账号模型 — 主表 + 扩展表模式

将 admins / doctors / users 三表合并为：
  - accounts         公共认证主表（手机号、用户名、密码、基础信息）
  - account_admins   管理员扩展表（角色、当前门店、邮箱）
  - account_doctors  医生扩展表（科室、职称、排班设置、展示设置）
  - account_users    用户/患者扩展表（微信、积分）

旧表 (admins / doctors / users) 保留不动，业务代码渐进式切换。
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base

# ---------------------------------------------------------------------------
# 统一账号主表
# ---------------------------------------------------------------------------

class Account(Base, AuditMixin):
    """统一账号主表 — 所有角色的公共认证与基础信息"""
    __tablename__ = "accounts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 租户关联（NULL = 平台管理员）
    tenant_id = Column(
        String(36), ForeignKey("tenants.id"), nullable=True, index=True,
        comment="租户ID（NULL表示平台账号）",
    )

    # --- 认证字段 ---
    phone = Column(String(20), index=True, comment="手机号")
    email = Column(String(100), index=True, comment="邮箱（租户内唯一）")
    username = Column(String(50), index=True, comment="用户名/登录账号")
    password_hash = Column(String(255), comment="密码哈希")

    # --- 基础信息 ---
    nickname = Column(String(50), comment="昵称")
    name = Column(String(50), comment="真实姓名")
    avatar = Column(String(255), comment="头像URL")
    gender = Column(Integer, default=0, comment="性别 0未知 1男 2女")
    status = Column(Integer, default=1, comment="状态 0禁用 1正常")

    # --- 登录审计 ---
    last_login_at = Column(DateTime, comment="最后登录时间")
    last_login_ip = Column(String(50), comment="最后登录IP")

    # --- 关联关系 ---
    tenant = relationship("Tenant", backref="accounts")

    # 约束：租户内 phone / username 唯一
    # PostgreSQL 中 NULL 不参与 UNIQUE 约束，因此平台管理员不受限制
    __table_args__ = (
        UniqueConstraint("tenant_id", "phone", name="uq_accounts_tenant_phone"),
        UniqueConstraint("tenant_id", "username", name="uq_accounts_tenant_username"),
        UniqueConstraint("tenant_id", "email", name="uq_accounts_tenant_email"),
        {"comment": "统一账号主表"},
    )


# ---------------------------------------------------------------------------
# 管理员扩展表
# ---------------------------------------------------------------------------

# 管理员-门店关联表（多对多，新表，对应旧的 admin_stores）
account_admin_stores = Table(
    "account_admin_stores",
    Base.metadata,
    Column(
        "account_id", String(36),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        primary_key=True, comment="账号ID",
    ),
    Column(
        "store_id", String(36),
        ForeignKey("stores.id", ondelete="CASCADE"),
        primary_key=True, comment="门店ID",
    ),
    Column("is_manager", Integer, default=0, comment="是否为该门店管理员: 0否 1是"),
    Column("created_at", DateTime, default=datetime.utcnow, comment="创建时间"),
)


class AccountAdmin(Base, AuditMixin):
    """管理员扩展表 — 一条 account 对应一条 account_admins"""
    __tablename__ = "account_admins"

    account_id = Column(
        String(36), ForeignKey("accounts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id = Column(String(36), ForeignKey("roles.id"), comment="角色ID")
    current_store_id = Column(
        String(36), ForeignKey("stores.id"), nullable=True,
        comment="当前选中门店ID",
    )
    email = Column(String(100), comment="邮箱")

    # --- 关联关系 ---
    account = relationship("Account", backref="admin_ext")
    role = relationship("Role", backref="account_admins")
    current_store = relationship("Store", foreign_keys=[current_store_id])
    stores = relationship(
        "Store",
        secondary=account_admin_stores,
        primaryjoin="AccountAdmin.account_id == account_admin_stores.c.account_id",
        secondaryjoin="Store.id == account_admin_stores.c.store_id",
        backref="account_admin_members",
    )

    __table_args__ = (
        {"comment": "管理员扩展表"},
    )


# ---------------------------------------------------------------------------
# 医生扩展表
# ---------------------------------------------------------------------------

class AccountDoctor(Base, AuditMixin):
    """医生扩展表 — 一条 account 对应一条 account_doctors"""
    __tablename__ = "account_doctors"

    account_id = Column(
        String(36), ForeignKey("accounts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    store_id = Column(String(36), ForeignKey("stores.id"), comment="所属门店ID")
    department_id = Column(
        String(36), ForeignKey("departments.id"), nullable=False,
        comment="所属科室ID",
    )
    role_id = Column(
        String(36), ForeignKey("roles.id"), nullable=True,
        comment="角色ID（关联 roles 表，支持 RBAC 权限）",
    )

    # --- 基础信息（医生特有） ---
    banner = Column(String(255), comment="医生banner图URL")
    title = Column(String(50), comment="职称")
    years_of_experience = Column(Integer, default=0, comment="医龄(年)")

    # --- 资质信息 ---
    education = Column(String(50), comment="学历")
    graduate_school = Column(String(100), comment="毕业院校")
    license_number = Column(String(100), comment="执业证书编号")
    license_image = Column(String(255), comment="执业证书图片URL")
    honors = Column(Text, comment="所获荣誉")

    # --- 坐诊设置 ---
    schedule_desc = Column(String(255), comment="坐诊时间说明")
    max_daily_appointments = Column(Integer, default=0, comment="每日最大接诊量,0表示不限制")
    online_consult_enabled = Column(Integer, default=0, comment="是否支持在线问诊 0否 1是")
    online_consult_fee = Column(Numeric(10, 2), default=0, comment="在线问诊费用")

    # --- 展示设置 ---
    page_style = Column(Integer, default=1, comment="页面风格 1/2/3")
    promo_video = Column(String(255), comment="宣传视频URL")
    tags = Column(String(255), comment="标签,逗号分隔")
    specialty = Column(Text, comment="擅长")
    introduction = Column(Text, comment="简介")

    # --- 其他设置 ---
    is_recommended = Column(Integer, default=0, comment="是否推荐 0否 1是")
    sort_order = Column(Integer, default=0, comment="排序")

    # --- 诊费设置 ---
    use_fee_template = Column(Integer, default=0, comment="是否使用诊费模板 0否 1是")

    # --- 软删除 ---
    deleted_at = Column(DateTime, nullable=True, comment="软删除时间")

    # --- 关联关系 ---
    account = relationship("Account", backref="doctor_ext")
    store = relationship("Store", backref="account_doctors")
    department = relationship("Department", backref="account_doctors")
    role = relationship("Role", backref="account_doctors")


# ---------------------------------------------------------------------------
# 用户/患者扩展表
# ---------------------------------------------------------------------------

class AccountUser(Base, AuditMixin):
    """用户扩展表 — 微信登录、积分等患者端特有字段"""
    __tablename__ = "account_users"

    account_id = Column(
        String(36), ForeignKey("accounts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # 冗余 tenant_id，用于唯一约束（值与 accounts.tenant_id 保持一致）
    tenant_id = Column(
        String(36), ForeignKey("tenants.id"), nullable=True, index=True,
        comment="租户ID（冗余，与 accounts.tenant_id 同步）",
    )
    role_id = Column(
        String(36), ForeignKey("roles.id"), nullable=True,
        comment="角色ID（关联 roles 表，支持 RBAC 权限）",
    )

    # --- 微信相关 ---
    openid = Column(String(100), index=True, comment="微信openid，租户内唯一")
    unionid = Column(String(100), index=True, nullable=True, comment="微信开放平台统一ID")
    wechat_nickname = Column(String(50), nullable=True, comment="微信原始昵称")
    wechat_avatar = Column(String(500), nullable=True, comment="微信原始头像URL")
    wechat_synced_at = Column(DateTime, nullable=True, comment="最后同步微信信息时间")

    # --- 积分 ---
    points = Column(Integer, default=0, comment="当前积分")

    # --- 关联关系 ---
    account = relationship("Account", backref="user_ext")
    tenant = relationship("Tenant")
    role = relationship("Role", backref="account_users")

    __table_args__ = (
        UniqueConstraint("tenant_id", "openid", name="uq_account_users_tenant_openid"),
        UniqueConstraint("tenant_id", "unionid", name="uq_account_users_tenant_unionid"),
        {"comment": "用户扩展表"},
    )
