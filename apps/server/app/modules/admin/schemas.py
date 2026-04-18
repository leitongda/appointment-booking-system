"""Shared admin DTOs."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class PermissionResponse(BaseModel):
    id: str
    code: str
    name: str
    type: str
    control_type: Optional[str] = Field(None, serialization_alias="controlType")
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
    control_type: Optional[str] = Field(None, max_length=20)
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

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )


class AdminCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: Optional[str] = Field(None, min_length=6, description="不填则默认为123456")
    name: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")
    role_id: Optional[str] = None
    store_id: Optional[str] = Field(None, description="当前门店ID（兼容旧版）")
    store_ids: Optional[List[str]] = Field(None, description="绑定的门店ID列表")
    status: int = Field(1, ge=0, le=1)


class AdminUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    password: Optional[str] = Field(None, min_length=6)
    name: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")
    role_id: Optional[str] = None
    store_id: Optional[str] = Field(None, description="当前门店ID（兼容旧版）")
    store_ids: Optional[List[str]] = Field(None, description="绑定的门店ID列表")
    status: Optional[int] = Field(None, ge=0, le=1)


class StoreInfo(BaseModel):
    id: str
    name: str
    logo: Optional[str] = None
    theme_style: Optional[str] = Field(None, serialization_alias="themeStyle")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "serialize_by_alias": True,
    }


class TenantStatusInfo(BaseModel):
    status: int
    subscription_plan_name: Optional[str] = Field(None, serialization_alias="subscriptionPlanName")
    subscription_end_at: Optional[datetime] = Field(None, serialization_alias="subscriptionEndAt")
    is_subscription_active: bool = Field(False, serialization_alias="isSubscriptionActive")
    days_until_expiry: Optional[int] = Field(None, serialization_alias="daysUntilExpiry")
    contact_phone: Optional[str] = Field(None, serialization_alias="contactPhone")

    model_config = {
        "populate_by_name": True,
        "serialize_by_alias": True,
    }


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
    current_store_id: Optional[str] = Field(None, serialization_alias="currentStoreId")
    current_store_name: Optional[str] = Field(None, serialization_alias="currentStoreName")
    store_id: Optional[str] = Field(None, serialization_alias="storeId")
    store_name: Optional[str] = Field(None, serialization_alias="storeName")
    store_ids: Optional[List[str]] = Field(None, serialization_alias="storeIds")
    stores: Optional[List[StoreInfo]] = None
    permissions: Optional[List[str]] = None
    is_super_admin: bool = Field(False, serialization_alias="isSuperAdmin")
    is_store_admin: bool = Field(False, serialization_alias="isStoreAdmin")
    can_view_all_stores: bool = Field(False, serialization_alias="canSwitchStores", validation_alias="can_view_all_stores")
    status: int
    last_login_at: Optional[datetime] = Field(None, serialization_alias="lastLoginAt")
    last_login_ip: Optional[str] = Field(None, serialization_alias="lastLoginIp")
    tenant_id: Optional[str] = Field(None, serialization_alias="tenantId")
    tenant: Optional[TenantStatusInfo] = None
    created_at: datetime = Field(..., serialization_alias="createdAt")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "serialize_by_alias": True,
    }


class AdminLoginRequest(BaseModel):
    username: str
    password: str
    encrypted: bool = True


class PhoneLoginRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11)
    password: str
    encrypted: bool = True


class SmsCodeRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11)


class SmsLoginRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11)
    code: str = Field(..., min_length=4, max_length=6)


class WechatQrcodeResponse(BaseModel):
    qrcode_url: str = Field(..., serialization_alias="qrcodeUrl")
    ticket: str
    expire_seconds: int = Field(..., serialization_alias="expireSeconds")

    class Config:
        populate_by_name = True


class WechatCheckResponse(BaseModel):
    status: str
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
    store: Optional[StoreInfo] = None
    stores: Optional[List[StoreInfo]] = None

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

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6, max_length=20)


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    avatar: Optional[str] = Field(None, max_length=255)


class SwitchStoreRequest(BaseModel):
    store_id: str = Field(..., description="目标门店ID")


class SwitchTenantRequest(BaseModel):
    tenant_id: str = Field(..., description="目标租户ID")


class TenantInfoResponse(BaseModel):
    id: str
    name: str
    tenant_code: str = Field(..., serialization_alias="tenantCode")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "serialize_by_alias": True,
    }


class OnlineUserResponse(BaseModel):
    admin_id: str = Field(..., serialization_alias="adminId")
    username: str
    name: Optional[str] = None
    role_name: Optional[str] = Field(None, serialization_alias="roleName")
    login_time: str = Field(..., serialization_alias="loginTime")
    login_ip: str = Field(..., serialization_alias="loginIp")
    user_agent: str = Field(..., serialization_alias="userAgent")
    device_info: dict = Field(..., serialization_alias="deviceInfo")
    ttl: int

    class Config:
        populate_by_name = True


class UserStatusResponse(BaseModel):
    admin_id: str = Field(..., serialization_alias="adminId")
    username: str
    name: Optional[str] = None
    role_name: Optional[str] = Field(None, serialization_alias="roleName")
    status: str
    login_time: Optional[str] = Field(None, serialization_alias="loginTime")
    login_ip: Optional[str] = Field(None, serialization_alias="loginIp")
    device_info: Optional[dict] = Field(None, serialization_alias="deviceInfo")
    ttl: Optional[int] = None
    last_login_at: Optional[str] = Field(None, serialization_alias="lastLoginAt")
    last_login_ip: Optional[str] = Field(None, serialization_alias="lastLoginIp")

    class Config:
        populate_by_name = True


class LoginHistoryResponse(BaseModel):
    id: str
    login_time: str = Field(..., serialization_alias="loginTime")
    logout_time: Optional[str] = Field(None, serialization_alias="logoutTime")
    logout_type: Optional[str] = Field(None, serialization_alias="logoutType")
    login_ip: Optional[str] = Field(None, serialization_alias="loginIp")
    browser: Optional[str] = None
    os: Optional[str] = None
    device_type: Optional[str] = Field(None, serialization_alias="deviceType")
    duration: Optional[int] = None

    class Config:
        populate_by_name = True
