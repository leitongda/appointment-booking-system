"""权限相关依赖

提供权限检查、门店访问控制等依赖函数。
支持 admin/doctor/user 三种角色的统一权限检查。

设计说明：
- require_permission / require_all_permissions: 仅 Admin 角色使用（依赖 get_current_admin）
- require_account_permission / require_account_all_permissions: 统一多角色使用（依赖 get_current_account）
"""
from typing import Callable, Union, List, Optional
from fastapi import HTTPException, Depends, status

# 重新导出认证依赖，因为权限依赖依赖它们
from app.common.auth_deps import get_current_admin
from app.common.auth_unified import get_current_account
from app.common.auth_types import AccountInfo, RoleType
from app.common.role_permissions import check_permission_match


def get_store_filter(current_admin: dict, allow_all: bool = False) -> Union[None, str, List[str]]:
    """
    获取门店过滤条件

    优先从 DataScope 读取规则，无 DataScope 时 fallback 到旧逻辑。

    Args:
        current_admin: 当前管理员信息
        allow_all: 是否允许查看所有绑定门店（聚合查看模式）

    Returns:
        - None: 超管或 scope_type=all，不过滤
        - str: 单个门店ID（当前选中门店）
        - List[str]: 多个门店ID列表（聚合查看模式）
    """
    if current_admin.get("is_super_admin"):
        return None

    # 优先读取 DataScope 配置
    data_scope = _resolve_data_scope(current_admin)
    if data_scope:
        scope_type = data_scope.get("scope_type")
        if scope_type == "all":
            return None
        if scope_type == "tenant":
            return None  # 租户级别，不过滤门店
        if scope_type == "store":
            current_store_id = current_admin.get("current_store_id") or current_admin.get("store_id")
            return current_store_id
        if scope_type == "custom":
            import json
            raw = data_scope.get("store_ids")
            if raw:
                if isinstance(raw, list):
                    return raw
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list) and parsed:
                        return parsed
                except (json.JSONDecodeError, TypeError):
                    pass
            return None

    # fallback: 旧逻辑
    store_ids = current_admin.get("store_ids", [])
    current_store_id = current_admin.get("current_store_id") or current_admin.get("store_id")

    # 聚合查看模式：返回所有绑定门店
    if allow_all and current_admin.get("can_view_all_stores") and len(store_ids) > 1:
        return store_ids

    # 默认返回当前选中门店
    return current_store_id


def _resolve_data_scope(current_admin: dict) -> Optional[dict]:
    """从 admin_info 中提取 data_scope 配置

    支持嵌套 role.data_scope 和平铺 data_scope 两种格式。
    """
    role = current_admin.get("role")
    if role and isinstance(role, dict):
        ds = role.get("data_scope")
        if ds:
            return ds
    return current_admin.get("data_scope")


def check_store_access(current_admin: dict, target_store_id: Optional[str]) -> bool:
    """
    检查当前管理员是否有权访问目标门店

    超级管理员可以访问任何门店
    其他用户只能访问绑定的门店
    """
    if current_admin.get("is_super_admin"):
        return True

    if not target_store_id:
        return False

    # 检查目标门店是否在绑定门店列表中
    store_ids = current_admin.get("store_ids", [])
    if store_ids and target_store_id in store_ids:
        return True

    # 兼容旧字段
    admin_store_id = current_admin.get("current_store_id") or current_admin.get("store_id")
    return admin_store_id == target_store_id


def get_effective_store_id(current_admin: dict, requested_store_id: Optional[str] = None) -> Optional[str]:
    """
    获取有效的门店ID（用于创建/更新操作）

    Args:
        current_admin: 当前管理员信息
        requested_store_id: 请求指定的门店ID

    Returns:
        有效的门店ID，如果无权限则抛出异常
    """
    # 超管可以指定任意门店
    if current_admin.get("is_super_admin"):
        return requested_store_id

    current_store_id = current_admin.get("current_store_id") or current_admin.get("store_id")

    # 如果指定了门店ID，验证权限
    if requested_store_id:
        if not check_store_access(current_admin, requested_store_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权操作此门店数据"
            )
        return requested_store_id

    # 默认使用当前选中门店
    return current_store_id


# ============================================================
# Admin 专用权限检查（保持向后兼容，已有路由继续使用）
# ============================================================

def require_permission(*permissions: str) -> Callable:
    """
    创建 Admin 权限检查依赖（保持向后兼容）

    用法:
        @router.post("")
        async def create_doctor(
            ...,
            _: None = Depends(require_permission("doctor:create"))
        ):
            ...

    或者检查多个权限（满足其中一个即可）:
        @router.put("")
        async def update_doctor(
            ...,
            _: None = Depends(require_permission("doctor:update", "doctor:create"))
        ):
            ...

    Args:
        *permissions: 需要的权限码，满足其中一个即可

    Returns:
        FastAPI 依赖函数
    """
    async def check_permission(current_admin: dict = Depends(get_current_admin)) -> None:
        # 超级管理员拥有所有权限
        if current_admin.get("is_super_admin"):
            return None

        admin_permissions = set(current_admin.get("permissions", []))

        # 检查是否拥有通配符权限
        if "*" in admin_permissions:
            return None

        # 检查是否拥有所需权限之一（支持通配符匹配）
        for perm in permissions:
            if check_permission_match(perm, admin_permissions):
                return None

        # 没有权限，抛出异常
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"需要权限: {', '.join(permissions)}"
        )

    return check_permission


def require_all_permissions(*permissions: str) -> Callable:
    """
    创建 Admin 权限检查依赖（需要满足所有权限，保持向后兼容）

    用法:
        @router.delete("")
        async def delete_all(
            ...,
            _: None = Depends(require_all_permissions("doctor:delete", "doctor:list"))
        ):
            ...

    Args:
        *permissions: 需要的权限码，必须全部满足

    Returns:
        FastAPI 依赖函数
    """
    async def check_all_permissions(current_admin: dict = Depends(get_current_admin)) -> None:
        # 超级管理员拥有所有权限
        if current_admin.get("is_super_admin"):
            return None

        admin_permissions = set(current_admin.get("permissions", []))

        # 检查是否拥有通配符权限
        if "*" in admin_permissions:
            return None

        # 检查是否拥有所有需要的权限（支持通配符匹配）
        missing = [p for p in permissions if not check_permission_match(p, admin_permissions)]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限: {', '.join(missing)}"
            )

        return None

    return check_all_permissions


# ============================================================
# 统一多角色权限检查（admin/doctor/user 均可使用）
# ============================================================

def _extract_permissions(account: AccountInfo) -> List[str]:
    """从 AccountInfo 中提取权限列表

    根据 role_type 从对应的 info 中获取 permissions 字段。
    - Admin: 从数据库 Role.permissions 加载
    - Doctor: 从 DOCTOR_PERMISSIONS 硬编码配置加载
    - User: 从 USER_PERMISSIONS 硬编码配置加载
    - Operator: 从 OPERATOR_PERMISSIONS 硬编码配置加载（复用 admin_info）
    """
    if account.role_type == RoleType.ADMIN and account.admin_info:
        return account.admin_info.permissions or []
    elif account.role_type == RoleType.DOCTOR and account.doctor_info:
        return account.doctor_info.permissions or []
    elif account.role_type == RoleType.USER and account.user_info:
        return account.user_info.permissions or []
    elif account.role_type == RoleType.OPERATOR and account.admin_info:
        # Operator 复用 AdminInfo 结构，权限从数据库 Role.permissions 加载
        return account.admin_info.permissions or []
    return []


def require_account_permission(*permissions: str) -> Callable:
    """
    创建统一权限检查依赖（支持 admin/doctor/user 三种角色）

    与 require_permission 不同，此函数通过 get_current_account 获取账号信息，
    自动根据角色类型加载对应的权限列表进行检查。

    用法:
        # 医生端路由
        @router.get("/schedule")
        async def get_my_schedule(
            ...,
            _: None = Depends(require_account_permission("doctor:schedule:view"))
        ):
            ...

        # 患者端路由
        @router.post("/appointment")
        async def create_appointment(
            ...,
            _: None = Depends(require_account_permission("patient:appointment:create"))
        ):
            ...

    权限检查逻辑：
    - Admin: 从数据库 Role.permissions 加载（超级管理员拥有全部权限）
    - Doctor: 从 DOCTOR_PERMISSIONS 硬编码配置加载
    - User: 从 USER_PERMISSIONS 硬编码配置加载
    - 支持通配符: "*" 匹配全部, "prefix:*" 匹配前缀下的所有权限

    Args:
        *permissions: 需要的权限码，满足其中一个即可

    Returns:
        FastAPI 依赖函数
    """
    async def check_permission(
        current_account: AccountInfo = Depends(get_current_account),
    ) -> None:
        # 超级管理员拥有所有权限
        if current_account.is_super_admin:
            return None

        account_permissions = set(_extract_permissions(current_account))

        # 检查是否拥有通配符权限
        if "*" in account_permissions:
            return None

        # 检查是否拥有所需权限之一（支持通配符匹配）
        for perm in permissions:
            if check_permission_match(perm, account_permissions):
                return None

        # 没有权限，抛出异常
        role_names = {
            RoleType.ADMIN: "管理员",
            RoleType.DOCTOR: "医生",
            RoleType.USER: "用户",
            RoleType.OPERATOR: "运营人员",
        }
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"需要权限: {', '.join(permissions)}（当前角色: {role_names.get(current_account.role_type, '未知')}）"
        )

    return check_permission


def require_account_all_permissions(*permissions: str) -> Callable:
    """
    创建统一权限检查依赖（需要满足所有权限，支持 admin/doctor/user）

    用法:
        @router.delete("")
        async def delete_all(
            ...,
            _: None = Depends(require_account_all_permissions("doctor:delete", "doctor:list"))
        ):
            ...

    Args:
        *permissions: 需要的权限码，必须全部满足

    Returns:
        FastAPI 依赖函数
    """
    async def check_all_permissions(
        current_account: AccountInfo = Depends(get_current_account),
    ) -> None:
        # 超级管理员拥有所有权限
        if current_account.is_super_admin:
            return None

        account_permissions = set(_extract_permissions(current_account))

        # 检查是否拥有通配符权限
        if "*" in account_permissions:
            return None

        # 检查是否拥有所有需要的权限（支持通配符匹配）
        missing = [p for p in permissions if not check_permission_match(p, account_permissions)]
        if missing:
            role_names = {
                RoleType.ADMIN: "管理员",
                RoleType.DOCTOR: "医生",
                RoleType.USER: "用户",
            }
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限: {', '.join(missing)}（当前角色: {role_names.get(current_account.role_type, '未知')}）"
            )

        return None

    return check_all_permissions
