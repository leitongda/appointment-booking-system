"""管理员和角色模型"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin
from datetime import datetime
import uuid


# 角色-权限关联表
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', String(36), ForeignKey('roles.id'), primary_key=True),
    Column('permission', String(100), primary_key=True),  # 权限标识，如 doctor:create, department:list
)


class Permission(Base, TimestampMixin):
    """权限表"""
    __tablename__ = "permissions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(100), unique=True, nullable=False, comment="权限码，如 doctor:create")
    name = Column(String(100), nullable=False, comment="权限名称")
    type = Column(String(20), nullable=False, comment="类型: menu/button")
    parent_code = Column(String(100), comment="父级权限码")
    icon = Column(String(50), comment="图标（菜单权限可用）")
    sort = Column(Integer, default=0, comment="排序号")


class Role(Base, TimestampMixin):
    """角色表"""
    __tablename__ = "roles"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), nullable=False, comment="角色名称")
    code = Column(String(50), unique=True, nullable=False, comment="角色编码")
    description = Column(String(200), comment="描述")
    status = Column(Integer, default=1, comment="状态 0禁用 1启用")
    
    # 权限列表（多对多）
    permissions = Column(Text, comment="权限列表，JSON格式")
    
    # 关联的管理员
    admins = relationship("Admin", back_populates="role")


class Admin(Base, TimestampMixin):
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
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True, comment="所属门店ID，超级管理员为空")
    status = Column(Integer, default=1, comment="状态 0禁用 1启用")
    last_login_at = Column(DateTime, comment="最后登录时间")
    last_login_ip = Column(String(50), comment="最后登录IP")
    
    # 关联角色
    role = relationship("Role", back_populates="admins")
    # 关联门店
    store = relationship("Store", backref="admins")


class OperationLog(Base):
    """操作日志表"""
    __tablename__ = "operation_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id = Column(String(36), ForeignKey("admins.id"), comment="操作人ID")
    admin_name = Column(String(50), comment="操作人姓名")
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

