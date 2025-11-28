"""认证依赖"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.doctor import Doctor

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
    """获取当前管理员"""
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
        # 从 Admin 表获取管理员
        result = await db.execute(select(Admin).where(Admin.id == admin_id))
        admin = result.scalar_one_or_none()
        
        if admin:
            if admin.status != 1:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
            
            return {
                "id": admin.id,
                "username": admin.username,
                "name": admin.name or "管理员",
                "phone": admin.phone,
                "status": admin.status,
                "role_id": admin.role_id,
                "is_admin": True,
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
        "is_admin": True,
    }


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict | None:
    """获取可选的当前用户（用于不强制登录的接口）"""
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
