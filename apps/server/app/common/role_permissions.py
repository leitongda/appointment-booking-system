"""统一角色权限配置

为不同角色类型定义权限列表。
- Admin 权限从数据库 Role.permissions 字段加载（已有逻辑）
- Doctor / User / Operator 权限暂用硬编码配置，后续可改为数据库配置
"""

# ============================================================
# 管理端排班权限定义
# ============================================================
ADMIN_SCHEDULE_PERMISSIONS: set[str] = {
    "schedule:read",               # 查看排班列表/详情/统计
    "schedule:create",             # 创建排班
    "schedule:update",             # 更新排班
    "schedule:delete",             # 删除排班
    "schedule:publish",            # 发布/撤回排班
    "schedule:suspend",            # 停诊/恢复排班
    "schedule:extra-quota",        # 申请加号
    "schedule:extra-quota:approve", # 审批加号
    "schedule:holiday",            # 节假日配置管理
    "schedule:room",               # 诊室管理
    "schedule:template",           # 排班模板/规则管理
}

# ============================================================
# 审批流权限定义
# ============================================================
ADMIN_APPROVAL_PERMISSIONS: set[str] = {
    "approval-flow:list",          # 查看流程定义
    "approval-flow:create",        # 创建流程定义
    "approval-flow:update",        # 编辑流程定义
    "approval-flow:manage",        # 激活/归档流程
    "approval-flow:delete",        # 删除流程
    "approval:read",               # 查看审批实例
    "approval:approve",            # 审批操作
    "approval-instance:manage",     # 回退/加签/跳转等实例管理操作
}

# ============================================================
# 医生权限定义
# ============================================================
DOCTOR_PERMISSIONS: set[str] = {
    # 排班相关
    "doctor:schedule:view",      # 查看自己的排班
    "doctor:schedule:edit",      # 编辑自己的排班
    "schedule:read",             # 排班读权限（查看排班列表/详情）
    "schedule:extra-quota",      # 申请加号
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
# 运营角色权限定义
# ============================================================
OPERATOR_PERMISSIONS: set[str] = {
    # 内容管理
    "content:news",              # 资讯管理
    "content:notice",            # 公告管理
    "content:banner",            # Banner 管理
    # 统计分析
    "statistics:read",           # 查看统计数据
    # 排班查看
    "schedule:read",             # 查看排班列表/详情
    # 预约查看
    "appointment:read",          # 查看预约列表/详情
    # 医生查看
    "doctor:read",               # 查看医生列表/详情
    # 患者查看
    "patient:read",              # 查看患者列表/详情
}

# ============================================================
# 患者（User）权限定义
# ============================================================
USER_PERMISSIONS: set[str] = {
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
SYSTEM_ROLES: dict[str, dict] = {
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
        "permissions": ["*"],
    },
    "TENANT_ADMIN": {
        "name": "租户管理员",
        "role_type": "admin",
        "is_default": False,
        "permissions": sorted(ADMIN_SCHEDULE_PERMISSIONS | ADMIN_APPROVAL_PERMISSIONS),
    },
    "STORE_ADMIN": {
        "name": "门店管理员",
        "role_type": "admin",
        "is_default": False,
        "permissions": [
            "schedule:read",
            "schedule:create",
            "schedule:update",
            "schedule:delete",
            "schedule:publish",
            "schedule:suspend",
            "schedule:extra-quota",
            "approval:read",
            "approval:approve",
        ],
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
    # --- Operator 角色 ---
    "OPERATOR": {
        "name": "运营人员",
        "role_type": "operator",
        "is_default": True,
        "permissions": list(OPERATOR_PERMISSIONS),
    },
}


def get_permissions_for_role_type(role_type: str) -> set[str]:
    """根据角色类型获取默认权限集合

    Args:
        role_type: 角色类型 - 'admin' / 'doctor' / 'user' / 'operator'

    Returns:
        该角色类型的默认权限集合
    """
    if role_type == "doctor":
        return DOCTOR_PERMISSIONS.copy()
    elif role_type == "user":
        return USER_PERMISSIONS.copy()
    elif role_type == "operator":
        return OPERATOR_PERMISSIONS.copy()
    # admin 的权限从数据库加载，这里返回空集合
    return set()


def check_permission_match(
    required: str,
    permissions: set[str],
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
    role_id: str | None,
    fallback: set[str],
) -> list[str]:
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
        import json

        from sqlalchemy import select as sa_select

        from app.models.admin import Role

        if hasattr(db, 'execute') and callable(db.execute):
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
