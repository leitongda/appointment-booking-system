"""认证依赖

提供用户、医生、管理员的认证依赖函数。

【重构说明】
原有 7 个认证函数已重构为 3 个统一函数（在 auth_unified.py 中）。
本文件保留旧函数作为包装器，调用新的统一函数，确保向后兼容。
渐进式迁移期间，现有 API 路由无需修改。
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional

from app.db.session import get_db
from app.core.security import decode_token
from app.core.redis import RedisCache
from app.models.user import User
from app.models.doctor import Doctor
from app.models.admin import Admin
from app.models.tenant import Tenant
from jose import jwt, JWTError
from app.core.config import settings
from app.middleware.tenant_context import (
    get_current_tenant_id,
    get_current_tenant_code,
    set_tenant_context,
)

# 导入新的统一认证函数
from app.common.auth_unified import (
    get_current_account,
    get_optional_account as get_optional_account_unified,
)
from app.common.auth_types import RoleType

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

    【重构】现在调用统一的 get_current_account 函数，
    然后转换为旧格式的 dict 返回，确保向后兼容。

    多租户支持：
    - 用户必须属于当前请求的租户
    - 如果请求有租户上下文，验证用户的 tenant_id 是否匹配
    - 同一手机号可在不同租户分别注册
    """
    from app.common.auth_unified import _get_user_account

    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供身份凭证，请先登录")

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="身份验证失败，请重新登录")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="身份验证失败，请重新登录")

    # 调用统一函数
    account = await _get_user_account(user_id, db)

    # 转换为旧格式（保持兼容）
    return account.to_dict()


async def get_current_doctor(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """获取当前医生用户（通过 User 表关联）

    【重构】验证用户是否是医生，如果是则返回医生信息。
    """
    if not current_user.get("is_doctor"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要医生权限，请联系管理员开通")

    doctor_id = current_user.get("doctor_id")
    if not doctor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="医生信息不存在，请检查后重试")

    # 调用统一函数获取医生信息
    from app.common.auth_unified import _get_doctor_account
    account = await _get_doctor_account(doctor_id, db)

    return {
        **current_user,
        "doctor": {
            "id": account.id,
            "name": account.name,
            "department_id": account.doctor_info.department_id if account.doctor_info else None,
            "title": account.doctor_info.title if account.doctor_info else None,
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

    【重构】现在调用统一的 _get_doctor_account 函数，
    然后从数据库加载 Doctor 对象返回（保持返回类型不变）。

    多租户支持：
    - 医生必须属于当前请求的租户
    - 如果请求有租户上下文，验证医生的 tenant_id 是否匹配
    """
    from app.common.auth_unified import _get_doctor_account

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

    # 调用统一函数验证
    await _get_doctor_account(doctor_id, db)

    # 获取 Doctor 对象（保持返回类型不变）
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

    return doctor


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """获取当前管理员（增强版，包含门店和角色信息）

    【重构】现在调用统一的 _get_admin_account 函数，
    然后转换为旧格式的 dict 返回，确保向后兼容。

    返回值包含：
    - current_store_id: 当前选中的门店ID
    - store_ids: 绑定的所有门店ID列表
    - can_view_all_stores: 是否可以查看所有门店（超管或多门店用户）
    - is_store_admin: 是否是门店管理员角色
    """
    from app.common.auth_unified import _get_admin_account

    # 处理未提供 Authorization header 的情况
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供身份凭证，请先登录")

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="身份验证失败，请重新登录")

    admin_id = payload.get("sub")
    token_type = payload.get("type", "")

    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="身份验证失败，请重新登录")

    # 检查是否是管理员 token
    if token_type == "admin" or "admin" in str(payload):
        # 调用统一函数
        account = await _get_admin_account(admin_id, db, token)
        return account.to_dict()

    # 兼容旧的 User 表管理员（遗留代码）
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
    """获取当前超级管理员（仅超级管理员可访问）

    【重构】保持原有逻辑，检查是否是超级管理员。
    """
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
    """获取可选的当前用户（用于不强制登录的接口）

    【重构】调用统一的 get_optional_account_unified 函数。
    """
    account = await get_optional_account_unified(credentials, db)
    if account:
        return account.to_dict()
    return None


async def get_current_user_or_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    获取当前用户或管理员
    同时支持普通用户和管理员访问的 API 使用此依赖

    【重构】调用统一的 get_current_account 函数，
    然后转换为旧格式的 dict 返回。
    """
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供身份凭证，请先登录")

    # 调用统一函数
    account = await get_current_account(credentials, db)
    return account.to_dict()
