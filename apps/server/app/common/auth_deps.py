"""认证依赖

提供用户、医生、管理员的认证依赖函数。
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
from app.models.tenant import Tenant
from jose import jwt, JWTError
from app.core.config import settings
from app.middleware.tenant_context import (
    get_current_tenant_id,
    get_current_tenant_code,
    set_tenant_context,
)

security = HTTPBearer(
    auto_error=False,
    scheme_name="JWT认证",
    description="在 Header 中携带 `Authorization: Bearer <token>`，Token 通过登录接口获取"
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """获取当前用户（增强版，包含租户校验）

    多租户支持：
    - 用户必须属于当前请求的租户
    - 如果请求有租户上下文，验证用户的 tenant_id 是否匹配
    - 同一手机号可在不同租户分别注册
    """
    # 处理未提供 Authorization header 的情况
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供身份凭证，请先登录")

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="身份验证失败，请重新登录")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="身份验证失败，请重新登录")

    # 从数据库获取用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不存在，请检查后重试")

    if user.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用，请联系管理员")

    # 多租户校验：如果请求有租户上下文，验证用户是否属于该租户
    current_tenant_id = get_current_tenant_id()
    current_tenant_code = get_current_tenant_code()
    if current_tenant_id and user.tenant_id:
        if user.tenant_id != current_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户不属于当前租户"
            )
    elif not current_tenant_id and not current_tenant_code and user.tenant_id:
        set_tenant_context(user.tenant_id)

    # 检查是否是医生
    doctor_result = await db.execute(select(Doctor).where(Doctor.user_id == user_id, Doctor.deleted_at.is_(None)))
    doctor = doctor_result.scalar_one_or_none()

    return {
        "id": user.id,
        "phone": user.phone,
        "nickname": user.nickname,
        "avatar": user.avatar,
        "gender": user.gender,
        "status": user.status,
        "tenant_id": user.tenant_id,
        "doctor_id": doctor.id if doctor else None,
        "is_doctor": doctor is not None,
    }


async def get_current_doctor(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """获取当前医生用户（通过 User 表关联）"""
    if not current_user.get("is_doctor"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要医生权限，请联系管理员开通")

    doctor_id = current_user.get("doctor_id")
    if not doctor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="医生信息不存在，请检查后重试")

    # 获取医生详情
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id, Doctor.deleted_at.is_(None)))
    doctor = result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="医生信息不存在，请检查后重试")

    if doctor.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="医生账号已被禁用，请联系管理员")

    return {
        **current_user,
        "doctor": {
            "id": doctor.id,
            "name": doctor.name,
            "department_id": doctor.department_id,
            "title": doctor.title,
        }
    }


async def get_current_doctor_by_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Doctor:
    """
    从医生 token 中获取当前医生
    用于医生端登录后的接口认证
    医生登录 token 的 sub 是 doctor.id，type 是 "doctor"

    多租户支持：
    - 医生必须属于当前请求的租户
    - 如果请求有租户上下文，验证医生的 tenant_id 是否匹配
    """
    from app.core.security import decode_token

    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供身份凭证，请先登录")

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="身份验证失败，请重新登录")

    doctor_id = payload.get("sub")
    token_type = payload.get("type", "")

    if not doctor_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="身份验证失败，请重新登录")

    # 验证是医生 token
    if token_type != "doctor":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的医生凭证，请使用医生账号登录")

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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="医生账号不存在，请检查后重试")

    if doctor.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="医生账号已被禁用，请联系管理员")

    # 检查门店状态
    if doctor.store and doctor.store.status == 2:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您所属的门店已被禁用，请联系管理员")

    # 多租户校验：如果请求有租户上下文，验证医生是否属于该租户
    current_tenant_id = get_current_tenant_id()
    current_tenant_code = get_current_tenant_code()
    if current_tenant_id and doctor.tenant_id:
        if doctor.tenant_id != current_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="医生不属于当前租户"
            )
    elif not current_tenant_id and not current_tenant_code and doctor.tenant_id:
        set_tenant_context(doctor.tenant_id)

    return doctor


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """获取当前管理员（增强版，包含门店和角色信息）

    返回值包含：
    - current_store_id: 当前选中的门店ID
    - store_ids: 绑定的所有门店ID列表
    - can_view_all_stores: 是否可以查看所有门店（超管或多门店用户）
    - is_store_admin: 是否是门店管理员角色
    """
    from app.models.admin import Admin

    # 处理未提供 Authorization header 的情况
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供身份凭证，请先登录")

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="身份验证失败，请重新登录")

    # 检查 Token 是否在黑名单中（优先使用 payload 中的 tenant_id，确保多租户隔离）
    token_hash = hashlib.sha256(token.encode()).hexdigest()[:32]
    token_tenant_id = payload.get("tenant_id")
    if await RedisCache.is_token_blacklisted(token_hash, tenant_id=token_tenant_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效，请重新登录")

    admin_id = payload.get("sub")
    token_type = payload.get("type", "")

    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="身份验证失败，请重新登录")

    # 检查是否是管理员 token
    if token_type == "admin" or "admin" in str(payload):
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

        if admin:
            if admin.status != 1:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用，请联系管理员")

            # 判断角色类型
            role_code = admin.role.code if admin.role else None
            role_name = admin.role.name if admin.role else None
            is_super_admin = role_code == "SUPER_ADMIN" or role_name == "超级管理员"
            is_store_admin = role_code == "STORE_ADMIN" or role_name == "门店管理员"
            is_tenant_admin = role_code == "TENANT_ADMIN" or role_name == "租户管理员"
            is_platform_admin = role_code == "PLATFORM_ADMIN" or role_name == "平台管理员" or is_super_admin

            # 检查租户状态（非平台管理员需要检查租户）
            tenant_info = None
            if admin.tenant_id and not is_platform_admin:
                if admin.tenant:
                    from app.middleware.exception import raise_business_http_error
                    from app.common.error_codes import TenantErrorCode
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
                    tenant_info = {
                        "id": admin.tenant.id,
                        "tenant_code": admin.tenant.tenant_code,
                        "name": admin.tenant.name,
                        "status": admin.tenant.status,
                    }

            current_tenant_id = get_current_tenant_id()
            current_tenant_code = get_current_tenant_code()
            if admin.tenant_id and not current_tenant_id and not current_tenant_code:
                set_tenant_context(
                    admin.tenant_id,
                    admin.tenant.tenant_code if admin.tenant else None,
                )

            # 新增：强制校验租户一致性
            # 非超管用户：验证请求上下文租户与账号租户一致
            if admin.tenant_id and not is_super_admin:
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
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您所属的门店已被禁用，请联系管理员")

            # 获取绑定的可用门店ID列表
            store_ids = [s.id for s in available_stores]

            # 检查当前选中门店是否可用
            current_store = admin.current_store
            if current_store and current_store.status == 2:
                # 当前门店被禁用，自动切换到第一个可用门店
                current_store = available_stores[0] if available_stores else None

            # 是否可以查看所有绑定门店（超管可查看所有，绑定多门店的用户可切换门店）
            can_switch_stores = is_super_admin or len(store_ids) > 1

            # 解析权限列表
            permissions = []
            if is_super_admin:
                # 超级管理员拥有所有权限
                permissions = ["*"]
            elif admin.role and admin.role.permissions:
                try:
                    permissions = json.loads(admin.role.permissions)
                except (json.JSONDecodeError, TypeError):
                    permissions = []

            return {
                "id": admin.id,
                "username": admin.username,
                "name": admin.name or "管理员",
                "phone": admin.phone,
                "status": admin.status,
                "role_id": admin.role_id,
                "role_code": role_code,
                "role_name": admin.role.name if admin.role else None,
                # 租户信息
                "tenant_id": admin.tenant_id,
                "tenant": tenant_info,
                # 多门店支持（只返回可用门店）
                "current_store_id": current_store.id if current_store else None,
                "current_store_name": current_store.name if current_store else None,
                "current_store_logo": current_store.logo if current_store else None,
                "current_store_theme": current_store.theme_style if current_store else None,
                "store_ids": store_ids,
                "stores": [{"id": s.id, "name": s.name, "logo": s.logo} for s in available_stores],
                # 兼容旧字段
                "store_id": current_store.id if current_store else None,
                "store_name": current_store.name if current_store else None,
                "store_logo": current_store.logo if current_store else None,
                "store_theme": current_store.theme_style if current_store else None,
                # 权限标志
                "is_admin": True,
                "is_super_admin": is_super_admin,
                "is_store_admin": is_store_admin,
                "is_tenant_admin": is_tenant_admin,
                "is_platform_admin": is_platform_admin,
                "can_view_all_stores": can_switch_stores,
                "can_switch_stores": can_switch_stores,
                # 权限列表
                "permissions": permissions,
            }

    # 兼容旧的 User 表管理员
    result = await db.execute(select(User).where(User.id == admin_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不存在，请检查后重试")

    if user.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用，请联系管理员")

    return {
        "id": user.id,
        "phone": user.phone,
        "name": user.nickname or "管理员",
        "status": user.status,
        "role_id": None,
        "role_code": None,
        "tenant_id": None,
        "tenant": None,
        "current_store_id": None,
        "store_ids": [],
        "stores": [],
        "store_id": None,
        "store_name": None,
        "is_admin": True,
        "is_super_admin": True,  # 旧用户默认为超级管理员
        "is_store_admin": False,
        "is_tenant_admin": False,
        "is_platform_admin": True,  # 旧用户默认为平台管理员
        "can_view_all_stores": True,
        "can_switch_stores": True,
        "permissions": ["*"],  # 旧用户默认拥有所有权限
    }


async def get_current_super_admin(
    current_admin: dict = Depends(get_current_admin)
) -> dict:
    """获取当前超级管理员（仅超级管理员可访问）"""
    if not current_admin.get("is_super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此操作仅限超级管理员"
        )
    return current_admin


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict | None:
    """获取可选的当前用户（用于不强制登录的接口）"""
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def get_current_user_or_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    获取当前用户或管理员
    同时支持普通用户和管理员访问的 API 使用此依赖
    """
    from app.models.admin import Admin

    # 处理未提供 Authorization header 的情况
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供身份凭证，请先登录")

    token = credentials.credentials

    # 先检查 token 是否过期，提供更明确的错误信息
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="身份验证失败，请重新登录")

    user_id = payload.get("sub")
    token_type = payload.get("type", "")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="身份验证失败，请重新登录")

    # 优先检查是否是管理员
    if token_type == "admin" or "admin" in str(payload):
        result = await db.execute(
            select(Admin)
            .options(
                selectinload(Admin.role),
                selectinload(Admin.current_store),
                selectinload(Admin.stores)
            )
            .where(Admin.id == user_id)
        )
        admin = result.scalar_one_or_none()

        if admin:
            if admin.status != 1:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用，请联系管理员")

            role_code = admin.role.code if admin.role else None
            role_name = admin.role.name if admin.role else None
            is_super_admin = role_code == "SUPER_ADMIN" or role_name == "超级管理员"
            is_store_admin = role_code == "STORE_ADMIN" or role_name == "门店管理员"
            store_ids = [s.id for s in admin.stores] if admin.stores else []

            return {
                "id": admin.id,
                "username": admin.username,
                "name": admin.name or "管理员",
                "phone": admin.phone,
                "status": admin.status,
                "role_id": admin.role_id,
                "role_code": role_code,
                "current_store_id": admin.current_store_id,
                "store_ids": store_ids,
                "store_id": admin.current_store_id,
                "store_name": admin.current_store.name if admin.current_store else None,
                "is_admin": True,
                "is_super_admin": is_super_admin,
                "is_store_admin": is_store_admin,
                "is_doctor": False,
                "doctor_id": None,
            }

    # 尝试从 User 表获取
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user:
        if user.status != 1:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用，请联系管理员")

        # 检查是否是医生
        doctor_result = await db.execute(select(Doctor).where(Doctor.user_id == user_id, Doctor.deleted_at.is_(None)))
        doctor = doctor_result.scalar_one_or_none()

        return {
            "id": user.id,
            "phone": user.phone,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "gender": user.gender,
            "status": user.status,
            "doctor_id": doctor.id if doctor else None,
            "is_doctor": doctor is not None,
            "is_admin": False,
            "is_super_admin": False,
            "store_id": None,
            "store_ids": [],
        }

    # 再次尝试 Admin 表（兼容旧 token）
    result = await db.execute(
        select(Admin)
        .options(
            selectinload(Admin.role),
            selectinload(Admin.current_store),
            selectinload(Admin.stores)
        )
        .where(Admin.id == user_id)
    )
    admin = result.scalar_one_or_none()

    if admin:
        if admin.status != 1:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用，请联系管理员")

        role_code = admin.role.code if admin.role else None
        role_name = admin.role.name if admin.role else None
        is_super_admin = role_code == "SUPER_ADMIN" or role_name == "超级管理员"
        is_store_admin = role_code == "STORE_ADMIN" or role_name == "门店管理员"
        store_ids = [s.id for s in admin.stores] if admin.stores else []

        return {
            "id": admin.id,
            "username": admin.username,
            "name": admin.name or "管理员",
            "phone": admin.phone,
            "status": admin.status,
            "role_id": admin.role_id,
            "role_code": role_code,
            "current_store_id": admin.current_store_id,
            "store_ids": store_ids,
            "store_id": admin.current_store_id,
            "store_name": admin.current_store.name if admin.current_store else None,
            "is_admin": True,
            "is_super_admin": is_super_admin,
            "is_store_admin": is_store_admin,
            "is_doctor": False,
            "doctor_id": None,
        }

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不存在，请检查后重试")
