"""管理员和角色模型"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base, AuditMixin
from datetime import datetime
import uuid


# 角色-权限关联表
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', String(36), ForeignKey('roles.id'), primary_key=True),
    Column('permission', String(100), primary_key=True),  # 权限标识，如 doctor:create, department:list
)


# 管理员-门店关联表（多对多）
admin_stores = Table(
    'admin_stores',
    Base.metadata,
    Column('admin_id', String(36), ForeignKey('admins.id', ondelete='CASCADE'), primary_key=True, comment='管理员ID'),
    Column('store_id', String(36), ForeignKey('stores.id', ondelete='CASCADE'), primary_key=True, comment='门店ID'),
    Column('is_manager', Integer, default=0, comment='是否为该门店管理员: 0否 1是'),
    Column('created_at', DateTime, default=datetime.utcnow, comment='创建时间'),
)


class Permission(Base, AuditMixin):
    """权限表"""
    __tablename__ = "permissions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(100), unique=True, nullable=False, comment="权限码，如 doctor:create")
    name = Column(String(100), nullable=False, comment="权限名称")
    type = Column(String(20), nullable=False, comment="类型: menu/button")
    control_type = Column(String(20), nullable=True, comment="控制类型: page/tab/action/api")
    parent_code = Column(String(100), comment="父级权限码")
    icon = Column(String(50), comment="图标（菜单权限可用）")
    sort = Column(Integer, default=0, comment="排序号")


class Role(Base, AuditMixin):
    """角色表（统一支持 admin/doctor/user 三种角色类型）"""
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), nullable=False, comment="角色名称")
    code = Column(String(50), index=True, comment="角色编码，租户内唯一（平台角色 tenant_id 为 NULL）")
    description = Column(String(200), comment="描述")
    status = Column(Integer, default=1, comment="状态 0禁用 1启用")
    # 角色类型：admin / doctor / user
    role_type = Column(String(20), nullable=False, server_default="admin", comment="角色类型: admin/doctor/user")
    # 是否为该角色类型的默认角色（每个 tenant + role_type 最多一个默认角色）
    is_default = Column(Boolean, nullable=False, server_default="0", comment="是否为默认角色")
    # 租户关联（多租户支持，NULL表示平台角色）
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID（NULL表示平台角色）")

    # 权限列表（JSON格式，对 admin 角色从数据库加载；doctor/user 暂用硬编码）
    permissions = Column(Text, comment="权限列表，JSON格式")

    # 关联的管理员
    admins = relationship("Admin", back_populates="role")
    tenant = relationship("Tenant", back_populates="roles")

    # 租户内唯一约束
    __table_args__ = (
        # 平台角色 (tenant_id = NULL) 和租户角色 (tenant_id != NULL) 的 code 分别唯一
        # 这里使用复合唯一约束
        {'comment': '角色表（多租户支持，统一角色类型）'},
    )


class Admin(Base, AuditMixin):
    """管理员表"""
    __tablename__ = "admins"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    name = Column(String(50), comment="姓名")
    phone = Column(String(20), comment="手机号")
    email = Column(String(100), comment="邮箱")
    avatar = Column(String(255), comment="头像")
    role_id = Column(String(36), ForeignKey("roles.id"), comment="角色ID")
    # 租户关联（多租户支持，NULL表示平台管理员）
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID（NULL表示平台管理员）")
    # 当前选中的门店（用于门店切换功能）
    current_store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, comment="当前选中门店ID，超级管理员可为空")
    status = Column(Integer, default=1, comment="状态 0禁用 1启用")
    must_change_password = Column(Boolean, default=False, nullable=False, comment="首次登录是否强制修改密码")
    last_login_at = Column(DateTime, comment="最后登录时间")
    last_login_ip = Column(String(50), comment="最后登录IP")

    # 关联关系
    role = relationship("Role", back_populates="admins")
    tenant = relationship("Tenant", back_populates="admins")
    # 当前选中门店（单个）
    current_store = relationship("Store", foreign_keys=[current_store_id], backref="current_admins")
    # 绑定的所有门店（多对多）
    stores = relationship("Store", secondary=admin_stores, backref="admin_members")


class OperationLog(Base):
    """操作日志表"""
    __tablename__ = "operation_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    # 保留旧字段以向后兼容
    admin_id = Column(String(36), ForeignKey("admins.id"), comment="操作人ID(兼容旧版)")
    admin_name = Column(String(50), comment="操作人姓名(兼容旧版)")
    # 新增角色相关字段
    actor_id = Column(String(36), comment="操作者ID")
    actor_name = Column(String(50), comment="操作者姓名")
    actor_role = Column(String(20), comment="操作者角色: admin/doctor/user")
    module = Column(String(50), comment="模块")
    action = Column(String(100), comment="操作")
    method = Column(String(10), comment="请求方法")
    path = Column(String(255), comment="请求路径")
    params = Column(Text, comment="请求参数")
    result = Column(String(20), comment="结果")
    ip = Column(String(50), comment="IP地址")
    user_agent = Column(String(255), comment="User-Agent")
    duration = Column(Integer, comment="耗时(毫秒)")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")


class AdminLoginHistory(Base):
    """管理员登录历史表"""
    __tablename__ = "admin_login_history"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id = Column(String(36), ForeignKey("admins.id"), nullable=False, comment="管理员ID")
    login_time = Column(DateTime, nullable=False, default=datetime.utcnow, comment="登录时间")
    logout_time = Column(DateTime, nullable=True, comment="退出时间")
    logout_type = Column(String(20), nullable=True, comment="退出类型: manual/timeout/kicked")
    login_ip = Column(String(50), comment="登录IP")
    user_agent = Column(String(500), comment="User-Agent字符串")
    browser = Column(String(50), comment="浏览器")
    os = Column(String(50), comment="操作系统")
    device_type = Column(String(20), comment="设备类型: desktop/mobile/tablet")
    duration = Column(Integer, nullable=True, comment="在线时长（秒）")
    
    # 关联管理员
    admin = relationship("Admin", backref="login_history")
