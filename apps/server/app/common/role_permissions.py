"""统一角色权限配置

为不同角色类型定义权限列表。
- Admin 权限从数据库 Role.permissions 字段加载（已有逻辑）
- Doctor / User 权限暂用硬编码配置，后续可改为数据库配置
"""
from typing import Dict, List, Optional, Set

# ============================================================
# 医生权限定义
# ============================================================
DOCTOR_PERMISSIONS: Set[str] = {
    # 排班相关
    "doctor:schedule:view",      # 查看自己的排班
    "doctor:schedule:edit",      # 编辑自己的排班
    # 预约相关
    "doctor:appointment:view",   # 查看预约
    "doctor:appointment:edit",   # 处理预约（接诊/完成/取消）
    # 患者相关
    "doctor:patient:view",       # 查看患者信息
    # 问诊相关
    "doctor:consultation:*",     # 问诊相关全部操作
    # 个人资料
    "doctor:profile:edit",       # 编辑个人资料
    # 消息通知
    "doctor:message:view",       # 查看消息
    # 统计
    "doctor:statistics:view",    # 查看个人统计
}

# ============================================================
# 患者（User）权限定义
# ============================================================
USER_PERMISSIONS: Set[str] = {
    # 预约相关
    "patient:appointment:create",    # 创建预约
    "patient:appointment:cancel",    # 取消预约
    "patient:appointment:view",      # 查看预约
    # 个人资料
    "patient:profile:edit",          # 编辑个人资料
    # 就诊人管理
    "patient:patient:manage",        # 管理就诊人（家庭成员）
    # 消息通知
    "patient:message:view",          # 查看消息
    # 评价
    "patient:review:create",         # 创建评价
    "patient:review:view",           # 查看评价
}

# ============================================================
# 系统预定义角色
# ============================================================
SYSTEM_ROLES: Dict[str, dict] = {
    # --- Admin 角色 ---
    "SUPER_ADMIN": {
        "name": "超级管理员",
        "role_type": "admin",
        "is_default": False,
        "permissions": ["*"],
    },
    "PLATFORM_ADMIN": {
        "name": "平台管理员",
        "role_type": "admin",
        "is_default": False,
        "permissions": [],  # 由数据库配置
    },
    "TENANT_ADMIN": {
        "name": "租户管理员",
        "role_type": "admin",
        "is_default": False,
        "permissions": [],  # 由数据库配置
    },
    "STORE_ADMIN": {
        "name": "门店管理员",
        "role_type": "admin",
        "is_default": False,
        "permissions": [],  # 由数据库配置
    },
    # --- Doctor 角色 ---
    "DOCTOR": {
        "name": "医生",
        "role_type": "doctor",
        "is_default": True,
        "permissions": list(DOCTOR_PERMISSIONS),
    },
    # --- User 角色 ---
    "PATIENT": {
        "name": "患者",
        "role_type": "user",
        "is_default": True,
        "permissions": list(USER_PERMISSIONS),
    },
}


def get_permissions_for_role_type(role_type: str) -> Set[str]:
    """根据角色类型获取默认权限集合

    Args:
        role_type: 角色类型 - 'admin' / 'doctor' / 'user'

    Returns:
        该角色类型的默认权限集合
    """
    if role_type == "doctor":
        return DOCTOR_PERMISSIONS.copy()
    elif role_type == "user":
        return USER_PERMISSIONS.copy()
    # admin 的权限从数据库加载，这里返回空集合
    return set()


def check_permission_match(
    required: str,
    permissions: Set[str],
) -> bool:
    """检查是否满足单个权限要求

    支持通配符匹配：
    - "*" 匹配所有权限
    - "prefix:*" 匹配 prefix 下的所有权限
      例如 "doctor:consultation:*" 匹配 "doctor:consultation:create"

    Args:
        required: 需要的权限码
        permissions: 当前拥有的权限集合

    Returns:
        是否匹配
    """
    # 全局通配符
    if "*" in permissions:
        return True

    # 精确匹配
    if required in permissions:
        return True

    # 前缀通配符匹配：检查是否有 "prefix:*" 形式的权限
    parts = required.split(":")
    for i in range(len(parts)):
        prefix = ":".join(parts[: i + 1]) + ":*"
        if prefix in permissions:
            return True

    return False


async def load_permissions_from_role(
    db,
    role_id: Optional[str],
    fallback: Set[str],
) -> List[str]:
    """从 Role 表加载权限，失败时返回 fallback

    Args:
        db: 数据库会话（同步或异步）
        role_id: 角色 ID
        fallback: 加载失败时的默认权限

    Returns:
        权限列表
    """
    if not role_id:
        return list(fallback)

    try:
        from sqlalchemy import select as sa_select
        from app.models.admin import Role
        import json

        if hasattr(db, 'execute') and hasattr(db.execute, '__call__'):
            result = await db.execute(sa_select(Role).where(Role.id == role_id))
            role = result.scalar_one_or_none()
        else:
            role = None

        if role and role.permissions:
            perms = json.loads(role.permissions)
            if isinstance(perms, list) and perms:
                return perms
    except Exception:
        pass

    return list(fallback)
