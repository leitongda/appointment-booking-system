"""统一认证类型定义

为多角色认证系统提供统一的数据结构，为后续统一账号表打基础。
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class RoleType(str, Enum):
    """角色类型枚举"""
    ADMIN = "admin"
    DOCTOR = "doctor"
    USER = "user"


@dataclass
class AdminInfo:
    """管理员额外信息"""
    # 角色信息
    role_id: Optional[str] = None
    role_code: Optional[str] = None
    role_name: Optional[str] = None

    # 权限列表
    permissions: List[str] = field(default_factory=list)

    # 门店信息
    current_store_id: Optional[str] = None
    current_store_name: Optional[str] = None
    current_store_logo: Optional[str] = None
    current_store_theme: Optional[str] = None
    store_ids: List[str] = field(default_factory=list)
    stores: List[Dict[str, Any]] = field(default_factory=list)

    # 租户信息
    tenant_id: Optional[str] = None
    tenant_name: Optional[str] = None
    tenant_code: Optional[str] = None
    tenant_status: Optional[int] = None

    # 角色标志（便于快速判断）
    is_super_admin: bool = False
    is_store_admin: bool = False
    is_tenant_admin: bool = False
    is_platform_admin: bool = False
    can_view_all_stores: bool = False
    can_switch_stores: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（兼容旧接口）"""
        return {
            "role_id": self.role_id,
            "role_code": self.role_code,
            "role_name": self.role_name,
            "permissions": self.permissions,
            "current_store_id": self.current_store_id,
            "current_store_name": self.current_store_name,
            "current_store_logo": self.current_store_logo,
            "current_store_theme": self.current_store_theme,
            "store_ids": self.store_ids,
            "stores": self.stores,
            "tenant_id": self.tenant_id,
            "tenant": {
                "id": self.tenant_id,
                "name": self.tenant_name,
                "tenant_code": self.tenant_code,
                "status": self.tenant_status,
            } if self.tenant_id else None,
            "is_super_admin": self.is_super_admin,
            "is_store_admin": self.is_store_admin,
            "is_tenant_admin": self.is_tenant_admin,
            "is_platform_admin": self.is_platform_admin,
            "can_view_all_stores": self.can_view_all_stores,
            "can_switch_stores": self.can_switch_stores,
        }


@dataclass
class DoctorInfo:
    """医生额外信息"""
    doctor_id: Optional[str] = None
    name: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    title: Optional[str] = None
    store_id: Optional[str] = None
    store_name: Optional[str] = None
    # 权限列表（从 DOCTOR_PERMISSIONS 或数据库角色配置加载）
    permissions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.doctor_id,
            "name": self.name,
            "department_id": self.department_id,
            "department_name": self.department_name,
            "title": self.title,
            "store_id": self.store_id,
            "store_name": self.store_name,
        }


@dataclass
class UserInfo:
    """用户额外信息"""
    openid: Optional[str] = None
    points: int = 0
    is_doctor: bool = False
    doctor_id: Optional[str] = None
    # 权限列表（从 USER_PERMISSIONS 或数据库角色配置加载）
    permissions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "openid": self.openid,
            "points": self.points,
            "is_doctor": self.is_doctor,
            "doctor_id": self.doctor_id,
        }


@dataclass
class AccountInfo:
    """统一账号信息

    支持三种角色类型：admin、doctor、user
    为后续统一账号表打基础，当前通过 role_type 区分不同角色。
    """
    # 基础信息（所有角色共有）
    id: str
    role_type: RoleType
    tenant_id: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    avatar: Optional[str] = None
    status: int = 1

    # 角色特定信息（根据 role_type 填充对应的 info）
    admin_info: Optional[AdminInfo] = None
    doctor_info: Optional[DoctorInfo] = None
    user_info: Optional[UserInfo] = None

    @property
    def is_admin(self) -> bool:
        """是否是管理员"""
        return self.role_type == RoleType.ADMIN

    @property
    def is_doctor(self) -> bool:
        """是否是医生"""
        return self.role_type == RoleType.DOCTOR

    @property
    def is_user(self) -> bool:
        """是否是普通用户"""
        return self.role_type == RoleType.USER

    @property
    def is_super_admin(self) -> bool:
        """是否是超级管理员"""
        return self.is_admin and self.admin_info and self.admin_info.is_super_admin

    @property
    def is_store_admin(self) -> bool:
        """是否是门店管理员"""
        return self.is_admin and self.admin_info and self.admin_info.is_store_admin

    @property
    def is_platform_admin(self) -> bool:
        """是否是平台管理员"""
        return self.is_admin and self.admin_info and self.admin_info.is_platform_admin

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（兼容旧的 dict 返回格式）

        这个方法确保新 API 与现有代码兼容，
        逐步迁移期间可以继续使用 dict 格式。
        """
        base = {
            "id": self.id,
            "role_type": self.role_type.value,
            "tenant_id": self.tenant_id,
            "phone": self.phone,
            "status": self.status,
        }

        if self.is_admin:
            admin_data = {
                "username": getattr(self, "username", None),
                "name": self.name,
                "avatar": self.avatar,
                "is_admin": True,
            }
            if self.admin_info:
                admin_data.update(self.admin_info.to_dict())
            base.update(admin_data)

        elif self.is_doctor:
            doctor_data = {
                "name": self.name,
                "avatar": self.avatar,
                "is_doctor": True,
                "is_admin": False,
            }
            if self.doctor_info:
                doctor_data["doctor"] = self.doctor_info.to_dict()
                doctor_data["doctor_id"] = self.doctor_info.doctor_id
                doctor_data["permissions"] = self.doctor_info.permissions
            base.update(doctor_data)

        elif self.is_user:
            user_data = {
                "nickname": self.name,  # User 表用 nickname
                "avatar": self.avatar,
                "gender": getattr(self, "gender", None),
                "is_admin": False,
                "is_doctor": False,
            }
            if self.user_info:
                user_data.update(self.user_info.to_dict())
                user_data["permissions"] = self.user_info.permissions
            base.update(user_data)

        return base

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccountInfo":
        """从字典创建 AccountInfo（用于兼容旧代码）"""
        role_type_str = data.get("role_type", "user")
        role_type = RoleType(role_type_str) if isinstance(role_type_str, str) else RoleType.USER

        admin_info = None
        doctor_info = None
        user_info = None

        if role_type == RoleType.ADMIN:
            admin_info = AdminInfo(
                role_id=data.get("role_id"),
                role_code=data.get("role_code"),
                role_name=data.get("role_name"),
                permissions=data.get("permissions", []),
                current_store_id=data.get("current_store_id"),
                current_store_name=data.get("current_store_name"),
                current_store_logo=data.get("current_store_logo"),
                current_store_theme=data.get("current_store_theme"),
                store_ids=data.get("store_ids", []),
                stores=data.get("stores", []),
                tenant_id=data.get("tenant_id"),
                is_super_admin=data.get("is_super_admin", False),
                is_store_admin=data.get("is_store_admin", False),
                is_tenant_admin=data.get("is_tenant_admin", False),
                is_platform_admin=data.get("is_platform_admin", False),
                can_view_all_stores=data.get("can_view_all_stores", False),
                can_switch_stores=data.get("can_switch_stores", False),
            )
        elif role_type == RoleType.DOCTOR:
            doctor = data.get("doctor", {})
            doctor_info = DoctorInfo(
                doctor_id=data.get("doctor_id") or doctor.get("id"),
                name=data.get("name") or doctor.get("name"),
                department_id=doctor.get("department_id"),
                title=doctor.get("title"),
            )
        elif role_type == RoleType.USER:
            user_info = UserInfo(
                openid=data.get("openid"),
                points=data.get("points", 0),
                is_doctor=data.get("is_doctor", False),
                doctor_id=data.get("doctor_id"),
            )

        return cls(
            id=data["id"],
            role_type=role_type,
            tenant_id=data.get("tenant_id"),
            phone=data.get("phone"),
            name=data.get("name") or data.get("nickname"),
            avatar=data.get("avatar"),
            status=data.get("status", 1),
            admin_info=admin_info,
            doctor_info=doctor_info,
            user_info=user_info,
        )
