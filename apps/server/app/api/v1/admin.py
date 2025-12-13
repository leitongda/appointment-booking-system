"""管理员和角色 API"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import json

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.services.admin_service import RoleService, AdminService, OperationLogService
from app.schemas.response import PageResponse
from app.core.security import create_access_token, create_refresh_token, get_rsa_public_key, rsa_decrypt
from app.core.config import settings

router = APIRouter()


# ========== Schemas ==========
class RoleCreate(BaseModel):
    name: str = Field(..., max_length=50)
    code: str = Field(..., max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    permissions: Optional[List[str]] = None
    status: int = Field(1, ge=0, le=1)


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    permissions: Optional[List[str]] = None
    status: Optional[int] = Field(None, ge=0, le=1)


class RoleResponse(BaseModel):
    id: str
    name: str
    code: str
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    status: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    name: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    role_id: Optional[str] = None
    status: int = Field(1, ge=0, le=1)


class AdminUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    password: Optional[str] = Field(None, min_length=6)
    name: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    role_id: Optional[str] = None
    status: Optional[int] = Field(None, ge=0, le=1)


class AdminResponse(BaseModel):
    id: str
    username: str
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    role_id: Optional[str] = Field(None, serialization_alias="roleId")
    role_name: Optional[str] = Field(None, serialization_alias="roleName")
    status: int
    last_login_at: Optional[datetime] = Field(None, serialization_alias="lastLoginAt")
    last_login_ip: Optional[str] = Field(None, serialization_alias="lastLoginIp")
    created_at: datetime = Field(..., serialization_alias="createdAt")

    class Config:
        from_attributes = True
        populate_by_name = True


class AdminLoginRequest(BaseModel):
    username: str
    password: str  # RSA 加密后的密码（Base64编码）
    encrypted: bool = True  # 是否加密，默认为 True


class PublicKeyResponse(BaseModel):
    public_key: str = Field(..., serialization_alias="publicKey")
    
    class Config:
        populate_by_name = True


class AdminLoginResponse(BaseModel):
    access_token: str = Field(..., serialization_alias="accessToken")
    refresh_token: str = Field(..., serialization_alias="refreshToken")
    expires_in: int = Field(..., serialization_alias="expiresIn")
    admin: AdminResponse

    class Config:
        populate_by_name = True


class OperationLogResponse(BaseModel):
    id: str
    admin_id: Optional[str] = None
    admin_name: Optional[str] = None
    module: Optional[str] = None
    action: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    params: Optional[str] = None
    result: Optional[str] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    duration: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


def parse_permissions(role) -> List[str]:
    """解析角色权限"""
    if role.permissions:
        try:
            return json.loads(role.permissions)
        except:
            return []
    return []


def build_role_response(role) -> RoleResponse:
    return RoleResponse(
        id=role.id,
        name=role.name,
        code=role.code,
        description=role.description,
        permissions=parse_permissions(role),
        status=role.status,
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


def build_admin_response(admin) -> AdminResponse:
    """构建管理员响应对象"""
    response = AdminResponse(
        id=admin.id,
        username=admin.username,
        name=admin.name,
        phone=admin.phone,
        email=admin.email,
        avatar=admin.avatar,
        role_id=admin.role_id,
        role_name=admin.role.name if admin.role else None,
        status=admin.status,
        last_login_at=admin.last_login_at,
        last_login_ip=admin.last_login_ip,
        created_at=admin.created_at,
    )
    return response


# ========== 管理员登录 ==========
@router.get("/public-key")
async def get_public_key():
    """获取 RSA 公钥（用于密码加密）"""
    from app.schemas.response import Response
    
    public_key = get_rsa_public_key()
    response_data = PublicKeyResponse(public_key=public_key)
    
    # 返回统一格式
    return Response(
        code=200,
        message="success",
        data=response_data.model_dump(by_alias=True)
    ).model_dump()


@router.post("/login")
async def admin_login(
    data: AdminLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """管理员登录
    
    密码需要使用 RSA 公钥加密后传输（Base64编码）
    """
    service = AdminService(db)
    
    # 解密密码
    try:
        if data.encrypted:
            password = rsa_decrypt(data.password)
        else:
            # 兼容未加密的情况（仅用于开发调试）
            password = data.password
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码解密失败")
    
    admin = await service.authenticate(data.username, password)
    
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    
    if admin.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
    
    # 更新登录信息
    client_ip = request.client.host if request.client else ""
    await service.update_login_info(admin.id, client_ip)
    
    # 生成Token
    access_token = create_access_token(data={"sub": admin.id, "type": "admin"})
    refresh_token = create_refresh_token(data={"sub": admin.id, "type": "admin"})
    
    response = AdminLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        admin=build_admin_response(admin),
    )
    return response.model_dump(by_alias=True)


@router.get("/me")
async def get_current_admin_info(
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """获取当前登录管理员信息"""
    service = AdminService(db)
    admin = await service.get_by_id(current_admin["id"])
    
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在")
    
    return build_admin_response(admin)


# ========== 角色管理 ==========
@router.get("/roles", response_model=PageResponse[RoleResponse])
async def get_roles(
    status: Optional[int] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取角色列表"""
    service = RoleService(db)
    items, total = await service.get_list(
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        data=[build_role_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/roles/all", response_model=List[RoleResponse])
async def get_all_roles(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取所有启用的角色（用于下拉选择）"""
    service = RoleService(db)
    items = await service.get_all()
    return [build_role_response(item) for item in items]


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取角色详情"""
    service = RoleService(db)
    role = await service.get_by_id(role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    return build_role_response(role)


@router.post("/roles", response_model=RoleResponse)
async def create_role(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """创建角色"""
    service = RoleService(db)
    try:
        role = await service.create(data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return build_role_response(role)


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """更新角色"""
    service = RoleService(db)
    try:
        role = await service.update(role_id, data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    return build_role_response(role)


@router.put("/roles/{role_id}/permissions")
async def update_role_permissions(
    role_id: str,
    permissions: List[str],
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """更新角色权限"""
    service = RoleService(db)
    role = await service.update_permissions(role_id, permissions)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    return {"message": "权限更新成功"}


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """删除角色"""
    service = RoleService(db)
    try:
        success = await service.delete(role_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    return {"message": "删除成功"}


# ========== 管理员管理 ==========
@router.get("/admins", response_model=PageResponse[AdminResponse])
async def get_admins(
    role_id: Optional[str] = None,
    status: Optional[int] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取管理员列表"""
    service = AdminService(db)
    items, total = await service.get_list(
        role_id=role_id,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        data=[build_admin_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/admins/{admin_id}", response_model=AdminResponse)
async def get_admin(
    admin_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取管理员详情"""
    service = AdminService(db)
    admin = await service.get_by_id(admin_id)
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在")
    return build_admin_response(admin)


@router.post("/admins", response_model=AdminResponse)
async def create_admin(
    data: AdminCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """创建管理员"""
    service = AdminService(db)
    try:
        admin = await service.create(data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    # 重新获取完整信息
    admin = await service.get_by_id(admin.id)
    return build_admin_response(admin)


@router.put("/admins/{admin_id}", response_model=AdminResponse)
async def update_admin(
    admin_id: str,
    data: AdminUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """更新管理员"""
    service = AdminService(db)
    try:
        admin = await service.update(admin_id, data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在")
    
    # 重新获取完整信息
    admin = await service.get_by_id(admin_id)
    return build_admin_response(admin)


@router.put("/admins/{admin_id}/reset-password")
async def reset_admin_password(
    admin_id: str,
    new_password: str = Query(..., min_length=6),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """重置管理员密码"""
    service = AdminService(db)
    success = await service.reset_password(admin_id, new_password)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在")
    return {"message": "密码重置成功"}


@router.delete("/admins/{admin_id}")
async def delete_admin(
    admin_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """删除管理员"""
    service = AdminService(db)
    try:
        success = await service.delete(admin_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在")
    return {"message": "删除成功"}


# ========== 操作日志 ==========
@router.get("/logs", response_model=PageResponse[OperationLogResponse])
async def get_operation_logs(
    admin_id: Optional[str] = None,
    module: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取操作日志列表"""
    service = OperationLogService(db)
    items, total = await service.get_list(
        admin_id=admin_id,
        module=module,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        data=[OperationLogResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )

