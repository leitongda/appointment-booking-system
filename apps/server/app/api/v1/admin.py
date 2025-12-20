"""管理员和角色 API"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import json

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.services.admin_service import RoleService, AdminService, OperationLogService, PermissionService
from app.schemas.response import PageResponse
from app.core.security import create_access_token, create_refresh_token, get_rsa_public_key, rsa_decrypt
from app.core.config import settings

router = APIRouter()


# ========== Schemas ==========
class PermissionResponse(BaseModel):
    id: str
    code: str
    name: str
    type: str
    parent_code: Optional[str] = Field(None, serialization_alias="parentCode")
    icon: Optional[str] = None
    sort: int = 0
    children: Optional[List["PermissionResponse"]] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class PermissionCreate(BaseModel):
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=100)
    type: str = Field(..., max_length=20)
    parent_code: Optional[str] = Field(None, max_length=100)
    icon: Optional[str] = Field(None, max_length=50)
    sort: int = Field(0, ge=0)


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
    password: Optional[str] = Field(None, min_length=6, description="不填则默认为123456")
    name: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    role_id: Optional[str] = None
    store_id: Optional[str] = Field(None, description="所属门店ID，门店管理员必填")
    status: int = Field(1, ge=0, le=1)


class AdminUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    password: Optional[str] = Field(None, min_length=6)
    name: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    role_id: Optional[str] = None
    store_id: Optional[str] = Field(None, description="所属门店ID")
    status: Optional[int] = Field(None, ge=0, le=1)


class StoreInfo(BaseModel):
    """门店简要信息（用于登录响应）"""
    id: str
    name: str
    logo: Optional[str] = None
    theme_style: Optional[str] = Field(None, serialization_alias="themeStyle")

    class Config:
        from_attributes = True
        populate_by_name = True


class AdminResponse(BaseModel):
    id: str
    username: str
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    role_id: Optional[str] = Field(None, serialization_alias="roleId")
    role_name: Optional[str] = Field(None, serialization_alias="roleName")
    role_code: Optional[str] = Field(None, serialization_alias="roleCode")
    store_id: Optional[str] = Field(None, serialization_alias="storeId")
    store_name: Optional[str] = Field(None, serialization_alias="storeName")
    permissions: Optional[List[str]] = None
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


class PhoneLoginRequest(BaseModel):
    """手机号+密码登录请求"""
    phone: str = Field(..., min_length=11, max_length=11)
    password: str
    encrypted: bool = True


class SmsCodeRequest(BaseModel):
    """发送短信验证码请求"""
    phone: str = Field(..., min_length=11, max_length=11)


class SmsLoginRequest(BaseModel):
    """短信验证码登录请求"""
    phone: str = Field(..., min_length=11, max_length=11)
    code: str = Field(..., min_length=4, max_length=6)


class WechatQrcodeResponse(BaseModel):
    """微信扫码二维码响应"""
    qrcode_url: str = Field(..., serialization_alias="qrcodeUrl")
    ticket: str
    expire_seconds: int = Field(..., serialization_alias="expireSeconds")

    class Config:
        populate_by_name = True


class WechatCheckResponse(BaseModel):
    """微信扫码状态响应"""
    status: str  # waiting/scanned/confirmed/expired
    access_token: Optional[str] = Field(None, serialization_alias="accessToken")
    refresh_token: Optional[str] = Field(None, serialization_alias="refreshToken")
    expires_in: Optional[int] = Field(None, serialization_alias="expiresIn")
    admin: Optional[AdminResponse] = None

    class Config:
        populate_by_name = True


class PublicKeyResponse(BaseModel):
    public_key: str = Field(..., serialization_alias="publicKey")
    
    class Config:
        populate_by_name = True


class AdminLoginResponse(BaseModel):
    access_token: str = Field(..., serialization_alias="accessToken")
    refresh_token: str = Field(..., serialization_alias="refreshToken")
    expires_in: int = Field(..., serialization_alias="expiresIn")
    admin: AdminResponse
    store: Optional[StoreInfo] = None  # 门店管理员登录时返回门店信息

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


def build_admin_response(admin, permissions: List[str] = None) -> AdminResponse:
    """构建管理员响应对象"""
    # 解析角色权限
    role_permissions = []
    if permissions is not None:
        role_permissions = permissions
    elif admin.role and admin.role.permissions:
        try:
            role_permissions = json.loads(admin.role.permissions)
        except:
            role_permissions = []
    
    response = AdminResponse(
        id=admin.id,
        username=admin.username,
        name=admin.name,
        phone=admin.phone,
        email=admin.email,
        avatar=admin.avatar,
        role_id=admin.role_id,
        role_name=admin.role.name if admin.role else None,
        role_code=admin.role.code if admin.role else None,
        store_id=admin.store_id,
        store_name=admin.store.name if admin.store else None,
        permissions=role_permissions,
        status=admin.status,
        last_login_at=admin.last_login_at,
        last_login_ip=admin.last_login_ip,
        created_at=admin.created_at,
    )
    return response


def build_store_info(store) -> Optional[StoreInfo]:
    """构建门店简要信息"""
    if not store:
        return None
    return StoreInfo(
        id=store.id,
        name=store.name,
        logo=store.logo,
        theme_style=store.theme_style,
    )


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
        store=build_store_info(admin.store),
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
    
    # 获取管理员权限
    perm_service = PermissionService(db)
    permissions = await perm_service.get_admin_permissions(admin.id)
    
    return build_admin_response(admin, permissions)


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6, max_length=20)


class UpdateProfileRequest(BaseModel):
    """更新个人信息请求"""
    name: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    avatar: Optional[str] = Field(None, max_length=255)


@router.put("/me")
async def update_current_admin_profile(
    data: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """更新当前管理员个人信息"""
    service = AdminService(db)
    admin = await service.update(current_admin["id"], data.model_dump(exclude_unset=True))
    
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在")
    
    # 重新获取完整信息
    admin = await service.get_by_id(current_admin["id"])
    return build_admin_response(admin)


@router.put("/me/change-password")
async def change_current_admin_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """修改当前管理员密码"""
    service = AdminService(db)
    admin = await service.get_by_id(current_admin["id"])
    
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在")
    
    # 验证旧密码
    from app.core.security import verify_password, get_password_hash
    if not verify_password(data.old_password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="原密码错误")
    
    # 更新密码
    admin.password_hash = get_password_hash(data.new_password)
    await db.commit()
    
    return {"message": "密码修改成功"}


# ========== 手机号登录 ==========
@router.post("/phone-login")
async def phone_login(
    data: PhoneLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """手机号+密码登录"""
    service = AdminService(db)
    
    # 解密密码
    try:
        if data.encrypted:
            password = rsa_decrypt(data.password)
        else:
            password = data.password
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码解密失败")
    
    admin = await service.authenticate_by_phone(data.phone, password)
    
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="手机号或密码错误")
    
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
        store=build_store_info(admin.store),
    )
    return response.model_dump(by_alias=True)


# ========== 短信验证码登录 ==========
@router.post("/sms/send")
async def send_sms_code(
    data: SmsCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    """发送登录验证码"""
    from app.services.sms_service import SmsService
    
    service = AdminService(db)
    
    # 检查手机号是否存在
    admin = await service.get_by_phone(data.phone)
    if not admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该手机号未注册")
    
    if admin.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
    
    try:
        await SmsService.send_code(data.phone, "login")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return {"message": "验证码已发送"}


@router.post("/sms/login")
async def sms_login(
    data: SmsLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """短信验证码登录"""
    from app.services.sms_service import SmsService
    
    service = AdminService(db)
    
    # 验证验证码
    is_valid = await SmsService.verify_code(data.phone, data.code, "login")
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")
    
    # 获取管理员
    admin = await service.get_by_phone(data.phone)
    if not admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该手机号未注册")
    
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
        store=build_store_info(admin.store),
    )
    return response.model_dump(by_alias=True)


# ========== 微信扫码登录 ==========
# 内存存储扫码状态（生产环境应使用 Redis）
_wechat_scan_tickets: dict = {}

@router.get("/wechat/qrcode")
async def get_wechat_qrcode():
    """获取微信扫码登录二维码
    
    注意：此为模拟实现，实际需要接入微信开放平台
    """
    import uuid
    import time
    
    ticket = str(uuid.uuid4())
    expire_seconds = 300
    
    # 存储票据状态
    _wechat_scan_tickets[ticket] = {
        "status": "waiting",
        "created_at": time.time(),
        "expire_at": time.time() + expire_seconds,
        "admin_id": None,
    }
    
    # 模拟二维码URL（实际应调用微信API生成）
    # 实际微信开放平台的 URL 格式类似：
    # https://open.weixin.qq.com/connect/qrconnect?appid=xxx&redirect_uri=xxx&...
    qrcode_url = f"https://example.com/wechat/scan?ticket={ticket}"
    
    response = WechatQrcodeResponse(
        qrcode_url=qrcode_url,
        ticket=ticket,
        expire_seconds=expire_seconds,
    )
    return response.model_dump(by_alias=True)


@router.get("/wechat/check")
async def check_wechat_scan(
    ticket: str = Query(...),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """检查微信扫码状态
    
    前端需要轮询此接口，直到返回 confirmed 或 expired
    """
    import time
    
    if ticket not in _wechat_scan_tickets:
        return WechatCheckResponse(status="expired").model_dump(by_alias=True)
    
    ticket_data = _wechat_scan_tickets[ticket]
    
    # 检查是否过期
    if time.time() > ticket_data["expire_at"]:
        del _wechat_scan_tickets[ticket]
        return WechatCheckResponse(status="expired").model_dump(by_alias=True)
    
    # 如果已确认（已扫码并绑定管理员）
    if ticket_data["status"] == "confirmed" and ticket_data["admin_id"]:
        service = AdminService(db)
        admin = await service.get_by_id(ticket_data["admin_id"])
        
        if admin and admin.status == 1:
            # 更新登录信息
            client_ip = request.client.host if request.client else ""
            await service.update_login_info(admin.id, client_ip)
            
            # 生成Token
            access_token = create_access_token(data={"sub": admin.id, "type": "admin"})
            refresh_token = create_refresh_token(data={"sub": admin.id, "type": "admin"})
            
            # 清理票据
            del _wechat_scan_tickets[ticket]
            
            response = WechatCheckResponse(
                status="confirmed",
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                admin=build_admin_response(admin),
            )
            return response.model_dump(by_alias=True)
    
    return WechatCheckResponse(status=ticket_data["status"]).model_dump(by_alias=True)


@router.post("/wechat/confirm")
async def confirm_wechat_scan(
    ticket: str = Query(...),
    admin_id: str = Query(..., description="管理员ID（模拟扫码确认用）"),
):
    """确认微信扫码（模拟接口，用于测试）
    
    实际项目中，这个接口应该由微信回调触发
    """
    import time
    
    if ticket not in _wechat_scan_tickets:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="票据不存在或已过期")
    
    ticket_data = _wechat_scan_tickets[ticket]
    
    if time.time() > ticket_data["expire_at"]:
        del _wechat_scan_tickets[ticket]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="票据已过期")
    
    # 更新状态为已确认
    ticket_data["status"] = "confirmed"
    ticket_data["admin_id"] = admin_id
    
    return {"message": "扫码确认成功"}


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
    store_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取管理员列表"""
    from app.api.deps import get_store_filter
    
    service = AdminService(db)
    
    # 门店过滤：门店管理员只能看到本门店的用户
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter
    
    items, total = await service.get_list(
        role_id=role_id,
        status=status,
        keyword=keyword,
        store_id=store_id,
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
    from app.api.deps import get_store_filter, check_store_access
    
    # 门店管理员只能在自己门店创建用户
    store_filter = get_store_filter(current_admin)
    if store_filter:
        if data.store_id and data.store_id != store_filter:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能在本门店创建用户")
        data.store_id = store_filter
    
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
    from app.api.deps import get_store_filter, check_store_access
    
    service = AdminService(db)
    
    # 检查权限
    admin = await service.get_by_id(admin_id)
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    
    # 门店管理员只能修改本门店用户
    store_filter = get_store_filter(current_admin)
    if store_filter:
        if not check_store_access(current_admin, admin.store_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改此用户")
        # 不允许修改用户的门店归属
        if data.store_id and data.store_id != store_filter:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改用户的门店归属")
    
    try:
        admin = await service.update(admin_id, data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
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


# ========== 权限管理 ==========
@router.get("/permissions/tree")
async def get_permissions_tree(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取权限树形结构（用于角色权限分配）"""
    service = PermissionService(db)
    tree = await service.get_tree()
    return tree


@router.get("/permissions/all")
async def get_all_permissions(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取所有权限（平铺列表）"""
    service = PermissionService(db)
    permissions = await service.get_all()
    return [
        {
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "type": p.type,
            "parentCode": p.parent_code,
            "icon": p.icon,
            "sort": p.sort,
        }
        for p in permissions
    ]


@router.post("/permissions")
async def create_permission(
    data: PermissionCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """创建权限（一般不需要手动创建，由初始化脚本管理）"""
    service = PermissionService(db)
    try:
        permission = await service.create(data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {
        "id": permission.id,
        "code": permission.code,
        "name": permission.name,
        "type": permission.type,
        "parentCode": permission.parent_code,
        "icon": permission.icon,
        "sort": permission.sort,
    }


@router.post("/permissions/batch")
async def batch_create_permissions(
    permissions: List[PermissionCreate],
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """批量创建权限"""
    service = PermissionService(db)
    created = await service.batch_create([p.model_dump() for p in permissions])
    return {"message": f"成功创建 {len(created)} 条权限"}


@router.delete("/permissions/{code}")
async def delete_permission(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """删除权限"""
    service = PermissionService(db)
    success = await service.delete(code)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="权限不存在")
    return {"message": "删除成功"}

