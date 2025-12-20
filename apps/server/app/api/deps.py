"""认证依赖"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional

from app.db.session import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.doctor import Doctor
from jose import jwt, JWTError
from app.core.config import settings

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """获取当前用户"""
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的Token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的Token")
    
    # 从数据库获取用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    
    if user.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
    
    # 检查是否是医生
    doctor_result = await db.execute(select(Doctor).where(Doctor.user_id == user_id))
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
    }


async def get_current_doctor(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """获取当前医生用户"""
    if not current_user.get("is_doctor"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要医生权限")
    
    doctor_id = current_user.get("doctor_id")
    if not doctor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="医生信息不存在")
    
    # 获取医生详情
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()
    
    if not doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="医生信息不存在")
    
    if doctor.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="医生账号已被禁用")
    
    return {
        **current_user,
        "doctor": {
            "id": doctor.id,
            "name": doctor.name,
            "department_id": doctor.department_id,
            "title": doctor.title,
        }
    }


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """获取当前管理员（增强版，包含门店和角色信息）"""
    from app.models.admin import Admin
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的Token")
    
    admin_id = payload.get("sub")
    token_type = payload.get("type", "")
    
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的Token")
    
    # 检查是否是管理员 token
    if token_type == "admin" or "admin" in str(payload):
        # 从 Admin 表获取管理员，同时加载关联的角色和门店
        result = await db.execute(
            select(Admin)
            .options(
                selectinload(Admin.role),
                selectinload(Admin.store)
            )
            .where(Admin.id == admin_id)
        )
        admin = result.scalar_one_or_none()
        
        if admin:
            if admin.status != 1:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
            
            # 判断是否是超级管理员
            role_code = admin.role.code if admin.role else None
            is_super_admin = role_code == "SUPER_ADMIN"
            
            return {
                "id": admin.id,
                "username": admin.username,
                "name": admin.name or "管理员",
                "phone": admin.phone,
                "status": admin.status,
                "role_id": admin.role_id,
                "role_code": role_code,
                "role_name": admin.role.name if admin.role else None,
                "store_id": admin.store_id,
                "store_name": admin.store.name if admin.store else None,
                "store_logo": admin.store.logo if admin.store else None,
                "store_theme": admin.store.theme_style if admin.store else None,
                "is_admin": True,
                "is_super_admin": is_super_admin,
            }
    
    # 兼容旧的 User 表管理员
    result = await db.execute(select(User).where(User.id == admin_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    
    if user.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
    
    return {
        "id": user.id,
        "phone": user.phone,
        "name": user.nickname or "管理员",
        "status": user.status,
        "role_id": None,
        "role_code": None,
        "store_id": None,
        "store_name": None,
        "is_admin": True,
        "is_super_admin": True,  # 旧用户默认为超级管理员
    }


def get_store_filter(current_admin: dict) -> Optional[str]:
    """
    获取门店过滤条件
    
    超级管理员返回 None（不过滤，可查看所有门店数据）
    门店管理员返回其 store_id（只能查看本门店数据）
    """
    if current_admin.get("is_super_admin"):
        return None
    return current_admin.get("store_id")


def check_store_access(current_admin: dict, target_store_id: Optional[str]) -> bool:
    """
    检查当前管理员是否有权访问目标门店
    
    超级管理员可以访问任何门店
    门店管理员只能访问自己的门店
    """
    if current_admin.get("is_super_admin"):
        return True
    
    admin_store_id = current_admin.get("store_id")
    if not admin_store_id:
        return False
    
    return admin_store_id == target_store_id


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
    
    token = credentials.credentials
    
    # 先检查 token 是否过期，提供更明确的错误信息
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token已过期，请重新登录")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的Token")
    
    user_id = payload.get("sub")
    token_type = payload.get("type", "")
    
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的Token")
    
    # 优先检查是否是管理员
    if token_type == "admin" or "admin" in str(payload):
        result = await db.execute(
            select(Admin)
            .options(
                selectinload(Admin.role),
                selectinload(Admin.store)
            )
            .where(Admin.id == user_id)
        )
        admin = result.scalar_one_or_none()
        
        if admin:
            if admin.status != 1:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
            
            role_code = admin.role.code if admin.role else None
            is_super_admin = role_code == "SUPER_ADMIN"
            
            return {
                "id": admin.id,
                "username": admin.username,
                "name": admin.name or "管理员",
                "phone": admin.phone,
                "status": admin.status,
                "role_id": admin.role_id,
                "role_code": role_code,
                "store_id": admin.store_id,
                "store_name": admin.store.name if admin.store else None,
                "is_admin": True,
                "is_super_admin": is_super_admin,
                "is_doctor": False,
                "doctor_id": None,
            }
    
    # 尝试从 User 表获取
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user:
        if user.status != 1:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
        
        # 检查是否是医生
        doctor_result = await db.execute(select(Doctor).where(Doctor.user_id == user_id))
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
        }
    
    # 再次尝试 Admin 表（兼容旧 token）
    result = await db.execute(
        select(Admin)
        .options(
            selectinload(Admin.role),
            selectinload(Admin.store)
        )
        .where(Admin.id == user_id)
    )
    admin = result.scalar_one_or_none()
    
    if admin:
        if admin.status != 1:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
        
        role_code = admin.role.code if admin.role else None
        is_super_admin = role_code == "SUPER_ADMIN"
        
        return {
            "id": admin.id,
            "username": admin.username,
            "name": admin.name or "管理员",
            "phone": admin.phone,
            "status": admin.status,
            "role_id": admin.role_id,
            "role_code": role_code,
            "store_id": admin.store_id,
            "store_name": admin.store.name if admin.store else None,
            "is_admin": True,
            "is_super_admin": is_super_admin,
            "is_doctor": False,
            "doctor_id": None,
        }
    
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
