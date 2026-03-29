"""认证依赖"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional, List, Union, Callable
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
                selectinload(Admin.tenant),
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
                    if admin.tenant.status == 0:
                        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="租户已被禁用")
                    if admin.tenant.status == 2:
                        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="租户已欠费，请续费后继续使用")
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
            can_view_all_stores = is_super_admin or len(store_ids) > 1

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
                "can_view_all_stores": can_view_all_stores,
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


# ==================== 租户相关依赖 ====================

async def get_current_tenant(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[dict]:
    """获取当前租户信息

    从请求上下文中获取租户信息（由 TenantContextMiddleware 设置）。
    如果租户不存在或未识别，返回 None。

    返回值包含：
    - id: 租户ID
    - tenant_code: 租户编码
    - name: 租户名称
    - status: 租户状态
    - subscription_plan_id: 当前订阅计划ID
    - is_subscription_active: 订阅是否有效
    """
    # 从上下文获取租户ID或编码
    tenant_id = get_current_tenant_id()
    tenant_code = get_current_tenant_code()

    # 也检查请求状态（中间件设置的）
    if not tenant_id and hasattr(request.state, 'tenant_id'):
        tenant_id = request.state.tenant_id
    if not tenant_code and hasattr(request.state, 'tenant_code'):
        tenant_code = request.state.tenant_code

    if not tenant_id and not tenant_code:
        return None

    # 从数据库获取租户信息
    query = select(Tenant).options(
        selectinload(Tenant.subscription_plan)
    )

    if tenant_id:
        query = query.where(Tenant.id == tenant_id)
    else:
        query = query.where(Tenant.tenant_code == tenant_code)

    result = await db.execute(query)
    tenant = result.scalar_one_or_none()

    if not tenant:
        return None

    # 检查租户状态
    if tenant.status == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="租户已被禁用"
        )

    return {
        "id": tenant.id,
        "tenant_code": tenant.tenant_code,
        "name": tenant.name,
        "status": tenant.status,
        "subscription_plan_id": tenant.subscription_plan_id,
        "subscription_start_at": tenant.subscription_start_at,
        "subscription_end_at": tenant.subscription_end_at,
        "is_subscription_active": tenant.is_subscription_active(),
        "max_stores": tenant.get_effective_max_stores(),
        "max_admins": tenant.get_effective_max_admins(),
        "max_doctors": tenant.get_effective_max_doctors(),
        "max_appointments_per_month": tenant.get_effective_max_appointments(),
    }


async def get_current_tenant_or_404(
    tenant: Optional[dict] = Depends(get_current_tenant)
) -> dict:
    """获取当前租户，如果不存在则返回404

    用于必须识别租户的接口。
    """
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="租户不存在或未识别"
        )
    return tenant


async def get_platform_admin(
    current_admin: dict = Depends(get_current_admin)
) -> dict:
    """获取平台管理员（仅平台管理员可访问）

    平台管理员是 tenant_id 为 NULL 的管理员。
    """
    if not current_admin.get("is_super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此操作仅限平台管理员"
        )
    return current_admin


def get_tenant_filter(current_admin: dict = Depends(get_current_admin)) -> Optional[str]:
    """获取租户过滤条件

    用于数据查询时自动添加租户过滤。

    Returns:
        - None: 平台管理员，不过滤，可查看所有租户数据
        - str: 租户ID，只能查看本租户数据
    """
    if current_admin.get("is_super_admin"):
        # 平台管理员可以查看所有租户数据
        return None

    # 租户管理员只能查看本租户数据
    return current_admin.get("tenant_id")


async def check_tenant_access(
    current_admin: dict,
    target_tenant_id: Optional[str],
    db: AsyncSession
) -> bool:
    """检查当前管理员是否有权访问目标租户

    平台管理员可以访问任何租户
    租户管理员只能访问自己的租户
    """
    if current_admin.get("is_super_admin"):
        return True

    if not target_tenant_id:
        return False

    admin_tenant_id = current_admin.get("tenant_id")
    return admin_tenant_id == target_tenant_id


async def get_tenant_from_admin(
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
) -> Optional[dict]:
    """从当前管理员获取租户信息

    如果管理员关联了租户，返回租户详情（含订阅计划状态）。
    平台管理员（tenant_id 为 NULL）返回 None。

    注意：tenant_id 直接从 admin 记录获取（P0 多租户修复后所有管理员均已关联 tenant_id），
    不再通过门店反查推断。
    """
    if current_admin.get("is_super_admin"):
        return None

    tenant_id = current_admin.get("tenant_id")
    if not tenant_id:
        return None

    # 获取租户详情
    result = await db.execute(
        select(Tenant).options(
            selectinload(Tenant.subscription_plan)
        ).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        return None

    return {
        "id": tenant.id,
        "tenant_code": tenant.tenant_code,
        "name": tenant.name,
        "status": tenant.status,
        "subscription_plan_id": tenant.subscription_plan_id,
        "is_subscription_active": tenant.is_subscription_active(),
    }


def require_tenant_admin() -> Callable:
    """创建租户管理员权限检查依赖

    确保当前用户是某个租户的管理员（非平台管理员）。
    """
    async def check_tenant_admin(
        current_admin: dict = Depends(get_current_admin),
        tenant: Optional[dict] = Depends(get_tenant_from_admin)
    ) -> dict:
        if current_admin.get("is_super_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="此接口仅限租户管理员访问"
            )

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="未关联租户"
            )

        return current_admin

    return check_tenant_admin


def require_platform_admin() -> Callable:
    """创建平台管理员权限检查依赖

    确保当前用户是平台管理员。
    """
    async def check_platform_admin(
        current_admin: dict = Depends(get_current_admin)
    ) -> dict:
        if not current_admin.get("is_super_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="此接口仅限平台管理员访问"
            )
        return current_admin

    return check_platform_admin


def check_tenant_role_access(current_admin: dict, required_role: str = None) -> None:
    """检查租户角色权限

    用于验证管理员是否有权访问当前租户数据。

    Args:
        current_admin: 当前管理员信息
        required_role: 可选的角色要求（如 "TENANT_ADMIN", "STORE_ADMIN"）

    Raises:
        HTTPException: 如果权限不足
    """
    # 平台管理员可以访问所有租户
    if current_admin.get("is_platform_admin") or current_admin.get("is_super_admin"):
        return

    # 获取当前租户上下文
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="需要租户上下文"
        )

    # 租户管理员只能访问本租户
    admin_tenant_id = current_admin.get("tenant_id")
    if admin_tenant_id and admin_tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该租户数据"
        )

    # 如果指定了角色要求，检查角色
    if required_role:
        role_code = current_admin.get("role_code", "")
        role_name = current_admin.get("role_name", "")

        # 角色匹配检查
        role_match = (
            role_code == required_role or
            role_name == required_role or
            # 租户管理员拥有门店管理员权限
            (required_role == "STORE_ADMIN" and role_code in ["TENANT_ADMIN", "SUPER_ADMIN"]) or
            # 超级管理员拥有所有权限
            role_code in ["SUPER_ADMIN", "PLATFORM_ADMIN"]
        )

        if not role_match:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要 {required_role} 角色"
            )


async def validate_tenant_consistency(
    db: AsyncSession,
    data: dict,
    tenant_id: str,
    related_fields: dict = None
) -> None:
    """验证关联数据的租户一致性

    在创建或更新数据时，验证所有关联数据都属于同一租户。

    Args:
        db: 数据库会话
        data: 要验证的数据字典
        tenant_id: 目标租户ID
        related_fields: 需要验证的关联字段配置
            {
                "store_id": Store,  # 字段名: 模型类
                "doctor_id": Doctor,
            }

    Raises:
        HTTPException: 如果关联数据不属于目标租户
    """
    if not related_fields:
        return

    for field_name, model_class in related_fields.items():
        field_value = data.get(field_name)
        if not field_value:
            continue

        # 查询关联数据的租户ID
        result = await db.execute(
            select(model_class).where(model_class.id == field_value)
        )
        related_obj = result.scalar_one_or_none()

        if not related_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} 不存在"
            )

        # 检查租户一致性
        related_tenant_id = getattr(related_obj, 'tenant_id', None)
        if related_tenant_id and related_tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{field_name} 不属于当前租户"
            )


def require_tenant_context() -> Callable:
    """创建租户上下文检查依赖

    确保请求有有效的租户上下文。
    用于公开预约接口等必须识别租户的场景。
    """
    async def check_tenant_context(
        tenant: Optional[dict] = Depends(get_current_tenant)
    ) -> dict:
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="缺少租户上下文，请通过 X-Tenant-ID 或 X-Tenant-Code 指定租户"
            )
        return tenant

    return check_tenant_context
