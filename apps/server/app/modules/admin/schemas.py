"""Shared admin DTOs."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.base import BaseSchema
from app.schemas.response import to_camel


class PermissionResponse(BaseModel):
    id: str
    code: str
    name: str
    type: str
    control_type: str | None = Field(None, serialization_alias="controlType")
    parent_code: str | None = Field(None, serialization_alias="parentCode")
    icon: str | None = None
    sort: int = 0
    children: list["PermissionResponse"] | None = None

    class Config:
        from_attributes = True
        populate_by_name = True

class PermissionCreate(BaseModel):
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=100)
    type: str = Field(..., max_length=20)
    control_type: str | None = Field(None, max_length=20)
    parent_code: str | None = Field(None, max_length=100)
    icon: str | None = Field(None, max_length=50)
    sort: int = Field(0, ge=0)

class RoleCreate(BaseModel):
    name: str = Field(..., max_length=50)
    code: str = Field(..., max_length=50)
    description: str | None = Field(None, max_length=200)
    permissions: list[str] | None = None
    status: int = Field(1, ge=0, le=1)

class RoleUpdate(BaseModel):
    name: str | None = Field(None, max_length=50)
    description: str | None = Field(None, max_length=200)
    permissions: list[str] | None = None
    status: int | None = Field(None, ge=0, le=1)

class RoleResponse(BaseModel):
    id: str
    name: str
    code: str
    description: str | None = None
    permissions: list[str] | None = None
    status: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )

class AdminCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str | None = Field(None, min_length=6, description="不填则使用系统默认密码")
    name: str | None = Field(None, max_length=50)
    phone: str | None = Field(None, max_length=20)
    email: str | None = Field(None, max_length=100)
    avatar: str | None = Field(None, max_length=255, description="头像URL")
    role_id: str | None = None
    store_id: str | None = Field(None, description="当前门店ID（兼容旧版）")
    store_ids: list[str] | None = Field(None, description="绑定的门店ID列表")
    status: int = Field(1, ge=0, le=1)

class AdminUpdate(BaseModel):
    username: str | None = Field(None, min_length=3, max_length=50)
    password: str | None = Field(None, min_length=6)
    name: str | None = Field(None, max_length=50)
    phone: str | None = Field(None, max_length=20)
    email: str | None = Field(None, max_length=100)
    avatar: str | None = Field(None, max_length=255, description="头像URL")
    role_id: str | None = None
    store_id: str | None = Field(None, description="当前门店ID（兼容旧版）")
    store_ids: list[str] | None = Field(None, description="绑定的门店ID列表")
    status: int | None = Field(None, ge=0, le=1)

class StoreInfo(BaseModel):
    id: str
    name: str
    logo: str | None = None
    theme_style: str | None = Field(None, serialization_alias="themeStyle")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "serialize_by_alias": True,
    }

class TenantStatusInfo(BaseModel):
    status: int
    subscription_plan_name: str | None = Field(None, serialization_alias="subscriptionPlanName")
    subscription_end_at: datetime | None = Field(None, serialization_alias="subscriptionEndAt")
    is_subscription_active: bool = Field(False, serialization_alias="isSubscriptionActive")
    days_until_expiry: int | None = Field(None, serialization_alias="daysUntilExpiry")
    contact_phone: str | None = Field(None, serialization_alias="contactPhone")

    model_config = {
        "populate_by_name": True,
        "serialize_by_alias": True,
    }

class AdminResponse(BaseModel):
    id: str
    username: str
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    avatar: str | None = None
    role_id: str | None = Field(None, serialization_alias="roleId")
    role_name: str | None = Field(None, serialization_alias="roleName")
    role_code: str | None = Field(None, serialization_alias="roleCode")
    current_store_id: str | None = Field(None, serialization_alias="currentStoreId")
    current_store_name: str | None = Field(None, serialization_alias="currentStoreName")
    store_id: str | None = Field(None, serialization_alias="storeId")
    store_name: str | None = Field(None, serialization_alias="storeName")
    store_ids: list[str] | None = Field(None, serialization_alias="storeIds")
    stores: list[StoreInfo] | None = None
    permissions: list[str] | None = None
    is_super_admin: bool = Field(False, serialization_alias="isSuperAdmin")
    is_store_admin: bool = Field(False, serialization_alias="isStoreAdmin")
    can_view_all_stores: bool = Field(False, serialization_alias="canSwitchStores", validation_alias="can_view_all_stores")
    status: int
    last_login_at: datetime | None = Field(None, serialization_alias="lastLoginAt")
    last_login_ip: str | None = Field(None, serialization_alias="lastLoginIp")
    tenant_id: str | None = Field(None, serialization_alias="tenantId")
    tenant: TenantStatusInfo | None = None
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
    access_token: str | None = Field(None, serialization_alias="accessToken")
    refresh_token: str | None = Field(None, serialization_alias="refreshToken")
    expires_in: int | None = Field(None, serialization_alias="expiresIn")
    admin: AdminResponse | None = None

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
    store: StoreInfo | None = None
    stores: list[StoreInfo] | None = None

    class Config:
        populate_by_name = True

class OperationLogResponse(BaseModel):
    id: str
    # 新字段：角色相关
    actor_id: str | None = None
    actor_name: str | None = None
    actor_role: str | None = None
    # 保留旧字段以向后兼容
    admin_id: str | None = None
    admin_name: str | None = None
    module: str | None = None
    action: str | None = None
    method: str | None = None
    path: str | None = None
    params: str | None = None
    result: str | None = None
    ip: str | None = None
    user_agent: str | None = None
    duration: int | None = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )

# NOTE: ChangePasswordRequest 已收敛到 app.schemas.common（统一密码策略 6-20 位）。
# 原定义 old_password 无 max_length，统一版补齐 max_length=20（收紧，符合只紧不松）。
# 请改为: from app.schemas.common import ChangePasswordRequest

class UpdateProfileRequest(BaseModel):
    name: str | None = Field(None, max_length=50)
    phone: str | None = Field(None, max_length=20)
    email: str | None = Field(None, max_length=100)
    avatar: str | None = Field(None, max_length=255)

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
    name: str | None = None
    role_name: str | None = Field(None, serialization_alias="roleName")
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
    name: str | None = None
    role_name: str | None = Field(None, serialization_alias="roleName")
    status: str
    login_time: str | None = Field(None, serialization_alias="loginTime")
    login_ip: str | None = Field(None, serialization_alias="loginIp")
    device_info: dict | None = Field(None, serialization_alias="deviceInfo")
    ttl: int | None = None
    last_login_at: str | None = Field(None, serialization_alias="lastLoginAt")
    last_login_ip: str | None = Field(None, serialization_alias="lastLoginIp")

    class Config:
        populate_by_name = True

class LoginHistoryResponse(BaseModel):
    id: str
    login_time: str = Field(..., serialization_alias="loginTime")
    logout_time: str | None = Field(None, serialization_alias="logoutTime")
    logout_type: str | None = Field(None, serialization_alias="logoutType")
    login_ip: str | None = Field(None, serialization_alias="loginIp")
    browser: str | None = None
    os: str | None = None
    device_type: str | None = Field(None, serialization_alias="deviceType")
    duration: int | None = None

    class Config:
        populate_by_name = True


# ==================== 账号使用统计 schemas ====================


class AccountStatsSummary(BaseSchema):
    """账号统计概览"""

    total_logins: int = Field(..., description="总登录次数")
    active_accounts: int = Field(..., description="活跃账号数")
    avg_duration_minutes: float = Field(..., description="平均使用时长(分钟)")
    total_duration_hours: float = Field(..., description="总使用时长(小时)")


class DeviceDistribution(BaseSchema):
    """设备/浏览器分布"""

    device_type: str
    count: int
    percentage: float


class HourlyDistribution(BaseSchema):
    """时段分布"""

    hour: int
    count: int


class AccountStatsDetail(BaseSchema):
    """单账号统计明细"""

    admin_id: str
    username: str
    name: str | None = None
    role_name: str | None = None
    login_count: int
    total_duration_seconds: int | None = None
    last_login_at: str | None = None
    last_login_ip: str | None = None
    primary_device: str | None = None
    primary_browser: str | None = None


class AccountStatsResponse(BaseSchema):
    """账号统计完整响应"""

    summary: AccountStatsSummary
    device_distribution: list[DeviceDistribution]
    browser_distribution: list[DeviceDistribution]
    hourly_distribution: list[HourlyDistribution]
    daily_trend: list[dict]
