import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, LargeBinary, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship as orm_relationship

from app.db.base import AuditMixin, Base


class User(Base, AuditMixin):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 租户关联（多租户支持，同一微信用户可在不同租户分别绑定账号）
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    phone = Column(String(20), index=True, nullable=True)  # 微信用户可无手机号，租户内唯一
    email = Column(String(100), index=True, nullable=True, comment="邮箱（租户内唯一）")
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(50))
    avatar = Column(String(255))
    gender = Column(Integer, default=0)  # 0未知 1男 2女
    openid = Column(String(100), index=True)  # 租户内唯一
    status = Column(Integer, default=1)  # 0禁用 1正常
    must_change_password = Column(Boolean, default=False, nullable=False, comment="首次登录是否强制修改密码")
    points = Column(Integer, default=0)  # 当前积分

    # 微信相关字段
    unionid = Column(String(100), index=True, nullable=True, comment="微信开放平台统一ID，租户内唯一")
    wechat_nickname = Column(String(50), nullable=True, comment="微信原始昵称")
    wechat_avatar = Column(String(500), nullable=True, comment="微信原始头像URL")
    wechat_synced_at = Column(DateTime, nullable=True, comment="最后同步微信信息时间")

    # 关联关系
    tenant = orm_relationship("Tenant", back_populates="users")
    patients = orm_relationship("Patient", back_populates="user")
    point_logs = orm_relationship("PointLog", back_populates="user")

    # 租户内唯一约束
    __table_args__ = (
        UniqueConstraint('tenant_id', 'phone', name='uq_users_tenant_phone'),
        UniqueConstraint('tenant_id', 'email', name='uq_users_tenant_email'),
        UniqueConstraint('tenant_id', 'openid', name='uq_users_tenant_openid'),
        UniqueConstraint('tenant_id', 'unionid', name='uq_users_tenant_unionid'),
        {'comment': '用户表（多租户支持）'},
    )

class Patient(Base, AuditMixin):
    __tablename__ = "patients"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    # 租户关联（多租户支持）
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, index=True, comment="首次就诊门店ID")
    name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False)
    id_card = Column(String(18))
    # 敏感数据加密列（阶段 1：新增，阶段 2：迁移数据，阶段 3：删除明文列）
    phone_encrypted = Column(LargeBinary, nullable=True, comment='手机号加密存储')
    phone_hash = Column(String(64), nullable=True, index=True, comment='手机号哈希（SHA-256）')
    id_card_encrypted = Column(LargeBinary, nullable=True, comment='身份证号加密存储')
    id_card_hash = Column(String(64), nullable=True, index=True, comment='身份证号哈希（SHA-256）')
    gender = Column(Integer)
    age = Column(Integer, comment="年龄")  # 新增年龄字段
    birthday = Column(DateTime)
    relationship = Column(String(20))  # 与账号用户关系
    is_default = Column(Boolean, default=False)

    # 新增字段
    card_no = Column(String(50), index=True)  # 就诊卡编号，租户内唯一
    province = Column(String(50))  # 省
    city = Column(String(50))  # 市
    district = Column(String(50))  # 区
    street = Column(String(100))  # 街道/社区
    id_card_type = Column(Integer, default=1)  # 证件类型: 1身份证 2户口簿 3护照
    ethnicity = Column(String(20), default="汉族")  # 民族
    address = Column(String(255))  # 详细地址
    source = Column(Integer, default=1)  # 来源: 1用户添加 2管理员添加
    total_consumption = Column(Numeric(10, 2), default=0)  # 累计消费

    # 关联关系
    tenant = orm_relationship("Tenant", back_populates="patients")
    user = orm_relationship("User", back_populates="patients")
    store = orm_relationship("Store", backref="patients")

    # 租户内唯一约束
    __table_args__ = (
        UniqueConstraint('tenant_id', 'card_no', name='uq_patients_tenant_card_no'),
        {'comment': '患者表（多租户支持）'},
    )

