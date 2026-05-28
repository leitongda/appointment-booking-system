"""统一认证函数

将原有的 7 个认证函数重构为 3 个核心函数：
1. get_current_account() - 统一认证入口
2. get_current_account_with_role() - 带角色验证的认证
3. get_optional_account() - 可选认证

为后续统一账号表打基础，当前保持与现有 Token 格式完全兼容。
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional
import hashlib
import json

from app.db.session import get_db
from app.core.security import decode_token
from app.core.redis import RedisCache
from app.models.user import User
from app.models.doctor import Doctor
from app.models.admin import Admin
from app.models.tenant import Tenant
from app.core.config import settings
from app.middleware.tenant_context import (
    get_current_tenant_id,
    get_current_tenant_code,
    set_tenant_context,
)
from app.middleware.exception import raise_business_http_error
from app.core.error_codes import ErrorCode as TenantErrorCode
from app.common.auth_types import (
    AccountInfo,
    RoleType,
    AdminInfo,
    DoctorInfo,
    UserInfo,
)
from app.common.role_permissions import get_permissions_for_role_type, DOCTOR_PERMISSIONS, USER_PERMISSIONS, load_permissions_from_role

# 开发环境导出用于测试
__all__ = [
    "get_current_account",
    "get_current_account_with_role",
    "get_optional_account",
]

security = HTTPBearer(
    auto_error=False,
    scheme_name="JWT认证",
    description="在 Header 中携带 `Authorization: Bearer <token>`，Token 通过登录接口获取"
)


async def _get_user_account(
    user_id: str,
    db: AsyncSession,
    check_tenant: bool = True,
) -> AccountInfo:
    """从 User 表获取账号信息（含医生检查）

    Args:
        user_id: 用户 ID
        db: 数据库会话
        check_tenant: 是否检查租户一致性

    Returns:
        AccountInfo 对象

    Raises:
        HTTPException: 用户不存在、被禁用或租户不匹配
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号不存在，请检查后重试"
        )

    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用，请联系管理员"
        )

    # 多租户校验
    current_tenant_id = get_current_tenant_id()
    current_tenant_code = get_current_tenant_code()
    if check_tenant and current_tenant_id and user.tenant_id:
        if user.tenant_id != current_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户不属于当前租户"
            )
    elif not current_tenant_id and not current_tenant_code and user.tenant_id:
        set_tenant_context(user.tenant_id)

    # 检查是否是医生
    doctor_result = await db.execute(
        select(Doctor).where(
            Doctor.user_id == user_id,
            Doctor.deleted_at.is_(None)
        )
    )
    doctor = doctor_result.scalar_one_or_none()

    # 尝试从 AccountUser.role_id 加载权限（fallback 到硬编码）
    user_role_id = None
    try:
        from app.models.account import AccountUser
        ext_result = await db.execute(
            select(AccountUser.role_id).where(AccountUser.account_id == user_id)
        )
        user_role_id = ext_result.scalar_one_or_none()
    except Exception:
        pass

    user_permissions = await load_permissions_from_role(db, user_role_id, USER_PERMISSIONS)

    user_info = UserInfo(
        openid=user.openid,
        points=user.points,
        is_doctor=doctor is not None,
        doctor_id=doctor.id if doctor else None,
        permissions=user_permissions,
    )

    return AccountInfo(
        id=user.id,
        role_type=RoleType.USER,
        tenant_id=user.tenant_id,
        phone=user.phone,
        name=user.nickname,
        avatar=user.avatar,
        status=user.status,
        user_info=user_info,
    )


async def _get_doctor_account(
    doctor_id: str,
    db: AsyncSession,
    check_tenant: bool = True,
    include_store_check: bool = True,
) -> AccountInfo:
    """从 Doctor 表获取账号信息

    Args:
        doctor_id: 医生 ID
        db: 数据库会话
        check_tenant: 是否检查租户一致性
        include_store_check: 是否检查门店状态

    Returns:
        AccountInfo 对象

    Raises:
        HTTPException: 医生不存在、被禁用或租户/门店不匹配
    """
    # 获取医生详情，同时加载关联的科室和门店
    result = await db.execute(
        select(Doctor)
        .options(
            selectinload(Doctor.department),
            selectinload(Doctor.store)
        )
        .where(Doctor.id == doctor_id, Doctor.deleted_at.is_(None))
    )
    doctor = result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="医生账号不存在，请检查后重试"
        )

    if doctor.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="医生账号已被禁用，请联系管理员"
        )

    # 检查门店状态
    if include_store_check and doctor.store and doctor.store.status == 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您所属的门店已被禁用，请联系管理员"
        )

    # 多租户校验
    current_tenant_id = get_current_tenant_id()
    current_tenant_code = get_current_tenant_code()
    if check_tenant and current_tenant_id and doctor.tenant_id:
        if doctor.tenant_id != current_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="医生不属于当前租户"
            )
    elif not current_tenant_id and not current_tenant_code and doctor.tenant_id:
        set_tenant_context(doctor.tenant_id)

    # 尝试从 AccountDoctor.role_id 加载权限（fallback 到硬编码）
    doctor_role_id = None
    try:
        from app.models.account import AccountDoctor
        ext_result = await db.execute(
            select(AccountDoctor.role_id).where(AccountDoctor.account_id == doctor_id)
        )
        doctor_role_id = ext_result.scalar_one_or_none()
    except Exception:
        pass

    doctor_permissions = await load_permissions_from_role(db, doctor_role_id, DOCTOR_PERMISSIONS)

    doctor_info = DoctorInfo(
        doctor_id=doctor.id,
        name=doctor.name,
        department_id=doctor.department_id,
        department_name=doctor.department.name if doctor.department else None,
        title=doctor.title,
        store_id=doctor.store_id,
        store_name=doctor.store.name if doctor.store else None,
        permissions=doctor_permissions,
    )

    return AccountInfo(
        id=doctor.id,
        role_type=RoleType.DOCTOR,
        tenant_id=doctor.tenant_id,
        phone=doctor.phone,
        name=doctor.name,
        avatar=doctor.avatar,
        status=doctor.status,
        doctor_info=doctor_info,
    )


async def _get_admin_account(
    admin_id: str,
    db: AsyncSession,
    token: str,
    check_tenant: bool = True,
    check_token_blacklist: bool = True,
) -> AccountInfo:
    """从 Admin 表获取账号信息（含完整的权限和租户校验）

    这是所有认证函数中最复杂的一个，包含：
    - Token 黑名单检查
    - 租户状态和订阅校验
    - 门店状态过滤
    - 权限解析

    Args:
        admin_id: 管理员 ID
        db: 数据库会话
        token: 原始 Token（用于黑名单检查）
        check_tenant: 是否检查租户一致性
        check_token_blacklist: 是否检查 Token 黑名单

    Returns:
        AccountInfo 对象

    Raises:
        HTTPException: 管理员不存在、被禁用、租户有问题等
    """
    # 检查 Token 是否在黑名单中（优先使用 payload 中的 tenant_id）
    if check_token_blacklist:
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:32]
        payload = decode_token(token)
        if payload:
            token_tenant_id = payload.get("tenant_id")
            if await RedisCache.is_token_blacklisted(token_hash, tenant_id=token_tenant_id):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="登录已失效，请重新登录"
                )

    # 从 Admin 表获取管理员，同时加载关联的角色、租户、当前门店和所有绑定门店
    result = await db.execute(
        select(Admin)
        .options(
            selectinload(Admin.role),
            selectinload(Admin.tenant).selectinload(Tenant.subscription_plan),
            selectinload(Admin.current_store),
            selectinload(Admin.stores)
        )
        .where(Admin.id == admin_id)
    )
    admin = result.scalar_one_or_none()

    if not admin:
        # 兼容旧的 User 表管理员（遗留代码，可逐步移除）
        result = await db.execute(select(User).where(User.id == admin_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="账号不存在，请检查后重试"
            )

        if user.status != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账号已被禁用，请联系管理员"
            )

        # 旧用户默认为超级管理员
        admin_info = AdminInfo(
            is_super_admin=True,
            is_store_admin=False,
            is_platform_admin=True,
            can_view_all_stores=True,
            can_switch_stores=True,
            permissions=["*"],
        )
        return AccountInfo(
            id=user.id,
            role_type=RoleType.ADMIN,
            phone=user.phone,
            name=user.nickname or "管理员",
            status=user.status,
            created_at=user.created_at,
            admin_info=admin_info,
        )

    if admin.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用，请联系管理员"
        )

    # 判断角色类型
    role_code = admin.role.code if admin.role else None
    role_name = admin.role.name if admin.role else None
    is_super_admin = role_code == "SUPER_ADMIN" or role_name == "超级管理员"
    is_store_admin = role_code == "STORE_ADMIN" or role_name == "门店管理员"
    is_tenant_admin = role_code == "TENANT_ADMIN" or role_name == "租户管理员"
    is_platform_admin = role_code == "PLATFORM_ADMIN" or role_name == "平台管理员" or is_super_admin

    # 填充租户元数据（所有有租户的管理员都需要，供 /me 等接口使用）
    tenant_id = admin.tenant_id
    tenant_name = None
    tenant_code = None
    tenant_status = None

    if admin.tenant_id and admin.tenant:
        tenant_id = admin.tenant.id
        tenant_name = admin.tenant.name
        tenant_code = admin.tenant.tenant_code
        tenant_status = admin.tenant.status

    # 检查租户状态（仅非平台管理员需要，平台管理员可跨租户操作）
    if admin.tenant_id and not is_platform_admin and admin.tenant:
        from datetime import datetime as _dt

        if admin.tenant.status == 0:
            raise_business_http_error(
                status.HTTP_403_FORBIDDEN,
                TenantErrorCode.TENANT_DISABLED,
                "租户已被禁用",
            )
        if admin.tenant.status == 2:
            raise_business_http_error(
                status.HTTP_403_FORBIDDEN,
                TenantErrorCode.TENANT_OVERDUE,
                "租户已欠费，请续费后继续使用",
            )
        # 防御：定时任务尚未把 status 改成 2 但订阅已到期的窗口期
        if (
            admin.tenant.status == 1
            and admin.tenant.subscription_end_at is not None
            and admin.tenant.subscription_end_at < _dt.utcnow()
        ):
            raise_business_http_error(
                status.HTTP_403_FORBIDDEN,
                TenantErrorCode.TENANT_OVERDUE,
                "订阅已到期，请续费后继续使用",
            )
        # 试用期到期同样按欠费处理（status=3 + 到期）
        if (
            admin.tenant.status == 3
            and admin.tenant.subscription_end_at is not None
            and admin.tenant.subscription_end_at < _dt.utcnow()
        ):
            raise_business_http_error(
                status.HTTP_403_FORBIDDEN,
                TenantErrorCode.TENANT_TRIAL_EXPIRED,
                "试用期已结束，请订阅后继续使用",
            )

    # 设置租户上下文
    current_tenant_id = get_current_tenant_id()
    current_tenant_code = get_current_tenant_code()
    if admin.tenant_id and not current_tenant_id and not current_tenant_code:
        set_tenant_context(
            admin.tenant_id,
            admin.tenant.tenant_code if admin.tenant else None,
        )

    # 强制校验租户一致性（非超管用户）
    if check_tenant and admin.tenant_id and not is_super_admin:
        if current_tenant_id and current_tenant_id != admin.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="当前请求的租户与账号不匹配",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 过滤禁用门店（status=2 表示禁用）
    available_stores = [s for s in admin.stores if s.status != 2] if admin.stores else []

    # 非超级管理员：如果所有绑定门店都被禁用，拒绝访问
    if not is_super_admin and admin.stores and not available_stores:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您所属的门店已被禁用，请联系管理员"
        )

    # 获取绑定的可用门店ID列表
    store_ids = [s.id for s in available_stores]

    # 检查当前选中门店是否可用
    current_store = admin.current_store
    if current_store and current_store.status == 2:
        # 当前门店被禁用，自动切换到第一个可用门店
        current_store = available_stores[0] if available_stores else None

    # 是否可以查看所有绑定门店
    can_switch_stores = is_super_admin or len(store_ids) > 1

    # 解析权限列表
    permissions = []
    if is_super_admin:
        permissions = ["*"]
    elif admin.role and admin.role.permissions:
        try:
            permissions = json.loads(admin.role.permissions)
        except (json.JSONDecodeError, TypeError):
            permissions = []

    # 计算租户过期天数
    days_until_expiry = None
    if admin.tenant and admin.tenant.subscription_end_at:
        from datetime import datetime as _dt
        delta = admin.tenant.subscription_end_at - _dt.utcnow()
        days_until_expiry = max(0, delta.days)

    admin_info = AdminInfo(
        role_id=admin.role_id,
        role_code=role_code,
        role_name=role_name,
        username=admin.username,
        permissions=permissions,
        current_store_id=current_store.id if current_store else None,
        current_store_name=current_store.name if current_store else None,
        current_store_logo=current_store.logo if current_store else None,
        current_store_theme=current_store.theme_style if current_store else None,
        store_ids=store_ids,
        stores=[{"id": s.id, "name": s.name, "logo": s.logo, "theme_style": s.theme_style} for s in available_stores],
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        tenant_code=tenant_code,
        tenant_status=tenant_status,
        tenant_subscription_plan_name=admin.tenant.subscription_plan.name if admin.tenant and admin.tenant.subscription_plan else None,
        tenant_subscription_end_at=admin.tenant.subscription_end_at if admin.tenant else None,
        tenant_is_subscription_active=admin.tenant.is_subscription_active if admin.tenant else False,
        tenant_days_until_expiry=days_until_expiry,
        tenant_contact_phone=admin.tenant.contact_phone if admin.tenant else None,
        is_super_admin=is_super_admin,
        is_store_admin=is_store_admin,
        is_tenant_admin=is_tenant_admin,
        is_platform_admin=is_platform_admin,
        can_view_all_stores=can_switch_stores,
        can_switch_stores=can_switch_stores,
    )

    return AccountInfo(
        id=admin.id,
        role_type=RoleType.ADMIN,
        tenant_id=admin.tenant_id,
        phone=admin.phone,
        email=admin.email,
        name=admin.name or "管理员",
        avatar=admin.avatar,
        status=admin.status,
        last_login_at=admin.last_login_at,
        last_login_ip=admin.last_login_ip,
        created_at=admin.created_at,
        admin_info=admin_info,
    )


async def get_current_account(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> AccountInfo:
    """统一认证入口

    根据 Token 中的 type 字段自动分发到对应的认证逻辑：
    - type="admin" → Admin 表认证
    - type="doctor" → Doctor 表认证
    - 其他 → User 表认证（默认）

    多租户支持：
    - 所有角色都支持租户校验
    - 如果请求有租户上下文，验证账号是否属于该租户
    - 如果请求没有租户上下文，自动设置账号的租户

    Returns:
        AccountInfo 对象，包含统一格式的账号信息

    Raises:
        HTTPException: 认证失败时抛出 401/403 错误
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供身份凭证，请先登录"
        )

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="身份验证失败，请重新登录"
        )

    account_id = payload.get("sub")
    if not account_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="身份验证失败，请重新登录"
        )

    token_type = payload.get("type", "")

    # 根据 Token 类型分发到不同的认证逻辑
    if token_type == "admin":
        return await _get_admin_account(account_id, db, token)
    elif token_type == "doctor":
        return await _get_doctor_account(account_id, db)
    else:
        # 默认为 User 表认证
        return await _get_user_account(account_id, db)


async def get_current_account_with_role(
    required_role: RoleType,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> AccountInfo:
    """带角色验证的统一认证

    在 get_current_account 基础上增加角色验证，
    用于需要特定角色才能访问的接口。

    Args:
        required_role: 要求的角色类型（admin/doctor/user）
        credentials: HTTP Bearer 凭证
        db: 数据库会话

    Returns:
        AccountInfo 对象

    Raises:
        HTTPException: 角色不匹配时抛出 403 错误
    """
    account = await get_current_account(credentials, db)

    if account.role_type != required_role:
        role_names = {
            RoleType.ADMIN: "管理员",
            RoleType.DOCTOR: "医生",
            RoleType.USER: "用户",
        }
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"需要{role_names[required_role]}权限，当前账号无权访问"
        )

    return account


async def get_optional_account(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[AccountInfo]:
    """可选的统一认证

    用于不强制登录的接口，如果提供了有效 Token 则返回账号信息，
    否则返回 None。

    Args:
        credentials: HTTP Bearer 凭证（可选）
        db: 数据库会话

    Returns:
        AccountInfo 对象或 None
    """
    if not credentials:
        return None

    try:
        return await get_current_account(credentials, db)
    except HTTPException:
        return None
