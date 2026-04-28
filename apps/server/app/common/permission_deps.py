"""权限相关依赖

提供权限检查、门店访问控制等依赖函数。
"""
from typing import Callable, Union, List, Optional
from fastapi import HTTPException, Depends

# 重新导出认证依赖，因为权限依赖依赖它们
from app.common.auth_deps import get_current_admin


def get_store_filter(current_admin: dict, allow_all: bool = False) -> Union[None, str, List[str]]:
    """
    获取门店过滤条件

    Args:
        current_admin: 当前管理员信息
        allow_all: 是否允许查看所有绑定门店（聚合查看模式）

    Returns:
        - None: 超管，不过滤，可查看所有门店数据
        - str: 单个门店ID（当前选中门店）
        - List[str]: 多个门店ID列表（聚合查看模式）
    """
    if current_admin.get("is_super_admin"):
        return None

    store_ids = current_admin.get("store_ids", [])
    current_store_id = current_admin.get("current_store_id") or current_admin.get("store_id")

    # 聚合查看模式：返回所有绑定门店
    if allow_all and current_admin.get("can_view_all_stores") and len(store_ids) > 1:
        return store_ids

    # 默认返回当前选中门店
    return current_store_id


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


def require_permission(*permissions: str) -> Callable:
    """
    创建权限检查依赖

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

        admin_permissions = current_admin.get("permissions", [])

        # 检查是否拥有通配符权限
        if "*" in admin_permissions:
            return None

        # 检查是否拥有所需权限之一
        for perm in permissions:
            if perm in admin_permissions:
                return None

        # 没有权限，抛出异常
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"需要权限: {', '.join(permissions)}"
        )

    return check_permission


def require_all_permissions(*permissions: str) -> Callable:
    """
    创建权限检查依赖（需要满足所有权限）

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

        admin_permissions = current_admin.get("permissions", [])

        # 检查是否拥有通配符权限
        if "*" in admin_permissions:
            return None

        # 检查是否拥有所有需要的权限
        missing = [p for p in permissions if p not in admin_permissions]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限: {', '.join(missing)}"
            )

        return None

    return check_all_permissions
