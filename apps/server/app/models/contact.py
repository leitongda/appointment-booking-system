"""通讯录相关模型

7 张表：
- Contact — 联系人主表
- ContactGroup — 联系人分组（树形）
- ContactTag — 联系人标签
- ContactGroupMember — 联系人-分组关联
- ContactTagMember — 联系人-标签关联
- ChannelAccount — 渠道账号配置
- ContactChannel — 联系人渠道信息
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import AuditMixin, Base


# ============================================================
# 关联表（多对多）
# ============================================================

contact_group_members = Table(
    "contact_group_members",
    Base.metadata,
    Column("contact_id", String(36), ForeignKey("contacts.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", String(36), ForeignKey("contact_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow),
)

contact_tag_members = Table(
    "contact_tag_members",
    Base.metadata,
    Column("contact_id", String(36), ForeignKey("contacts.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", String(36), ForeignKey("contact_tags.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow),
)


# ============================================================
# Contact — 联系人主表
# ============================================================

class Contact(Base, AuditMixin):
    """联系人 — 统一管理内部人员和外部联系人"""
    __tablename__ = "contacts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")

    # --- 基础信息 ---
    name = Column(String(100), nullable=False, comment="联系人姓名")
    nickname = Column(String(50), nullable=True, comment="昵称")
    avatar = Column(String(255), nullable=True, comment="头像URL")
    gender = Column(Integer, default=0, comment="性别 0未知 1男 2女")

    # --- 快捷联系方式（冗余，便于快速查询） ---
    phone = Column(String(20), nullable=True, index=True, comment="手机号")
    email = Column(String(100), nullable=True, index=True, comment="邮箱")

    # --- 类型标识 ---
    contact_type = Column(String(20), nullable=False, comment="联系人类型: patient/doctor/admin/staff/external")
    source_type = Column(String(20), nullable=True, comment="来源类型: admin/doctor/patient/manual_import")
    source_id = Column(String(36), nullable=True, comment="来源记录ID")

    # --- 关联到 Account 体系（可空） ---
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=True, index=True, comment="关联账号ID")

    # --- 组织信息 ---
    department_id = Column(String(36), nullable=True, comment="所属科室ID")
    store_id = Column(String(36), nullable=True, comment="所属门店ID")
    position = Column(String(50), nullable=True, comment="职位/职称")
    organization = Column(String(200), nullable=True, comment="所属机构（外部联系人用）")

    # --- 其他 ---
    notes = Column(Text, nullable=True, comment="备注")
    status = Column(Integer, default=1, comment="状态 0禁用 1正常")
    last_contact_at = Column(DateTime, nullable=True, comment="最后联系时间")
    deleted_at = Column(DateTime, nullable=True, comment="软删除时间")

    # --- 关联关系 ---
    groups = relationship("ContactGroup", secondary=contact_group_members, back_populates="contacts", lazy="selectin")
    tags = relationship("ContactTag", secondary=contact_tag_members, back_populates="contacts", lazy="selectin")
    channels = relationship("ContactChannel", back_populates="contact", cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        {"comment": "联系人表"}
    )


# ============================================================
# ContactGroup — 联系人分组
# ============================================================

class ContactGroup(Base, AuditMixin):
    """联系人分组（树形结构）"""
    __tablename__ = "contact_groups"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    name = Column(String(100), nullable=False, comment="分组名称")
    description = Column(String(500), nullable=True, comment="分组描述")
    parent_id = Column(String(36), ForeignKey("contact_groups.id"), nullable=True, comment="父分组ID")
    sort_order = Column(Integer, default=0, comment="排序")
    status = Column(Integer, default=1, comment="状态 0禁用 1正常")

    # --- 关联关系 ---
    children = relationship("ContactGroup", backref="parent", remote_side="ContactGroup.id", lazy="selectin")
    contacts = relationship("Contact", secondary=contact_group_members, back_populates="groups", lazy="selectin")

    __table_args__ = (
        {"comment": "联系人分组表"}
    )


# ============================================================
# ContactTag — 联系人标签
# ============================================================

class ContactTag(Base, AuditMixin):
    """联系人标签"""
    __tablename__ = "contact_tags"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    name = Column(String(50), nullable=False, comment="标签名称")
    color = Column(String(20), nullable=True, comment="标签颜色")
    sort_order = Column(Integer, default=0, comment="排序")

    # --- 关联关系 ---
    contacts = relationship("Contact", secondary=contact_tag_members, back_populates="tags", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_contact_tag_tenant_name"),
        {"comment": "联系人标签表"},
    )


# ============================================================
# ChannelAccount — 渠道账号配置
# ============================================================

class ChannelAccount(Base, AuditMixin):
    """渠道账号配置 — 管理各通知渠道的接入凭证"""
    __tablename__ = "channel_accounts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    store_id = Column(String(36), nullable=True, index=True, comment="门店ID（NULL=全局账号）")
    channel_type = Column(String(20), nullable=False, comment="渠道类型: sms/email/wechat/webhook")
    name = Column(String(100), nullable=False, comment="账号名称")
    config = Column(Text, nullable=False, comment="渠道配置JSON（敏感字段加密存储）")
    status = Column(Integer, default=1, comment="状态 0禁用 1正常 2验证中")
    is_default = Column(Integer, default=0, comment="是否为该渠道默认账号")
    last_sync_at = Column(DateTime, nullable=True, comment="最后同步/验证时间")
    last_error = Column(Text, nullable=True, comment="最后错误信息")

    __table_args__ = (
        {"comment": "渠道账号配置表"}
    )


# ============================================================
# ContactChannel — 联系人渠道信息
# ============================================================

class ContactChannel(Base):
    """联系人渠道信息 — 存储联系人在各渠道的标识"""
    __tablename__ = "contact_channels"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True, comment="联系人ID")
    channel_type = Column(String(20), nullable=False, comment="渠道类型: phone/email/wechat/sms")
    channel_value = Column(String(200), nullable=False, comment="渠道标识值（手机号/邮箱/openid）")
    is_primary = Column(Integer, default=0, comment="是否主要渠道")
    verified = Column(Integer, default=0, comment="是否已验证")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # --- 关联关系 ---
    contact = relationship("Contact", back_populates="channels")

    __table_args__ = (
        UniqueConstraint("contact_id", "channel_type", "channel_value", name="uq_contact_channel_value"),
        {"comment": "联系人渠道信息表"},
    )
