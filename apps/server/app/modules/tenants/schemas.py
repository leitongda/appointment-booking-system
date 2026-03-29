"""租户相关的 Pydantic Schema"""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal

from app.schemas.response import to_camel


# ==================== 订阅计划 ====================

class SubscriptionPlanBase(BaseModel):
    """订阅计划基础 Schema"""
    plan_code: str = Field(..., max_length=50, description="计划编码")
    name: str = Field(..., max_length=100, description="计划名称")
    description: Optional[str] = Field(None, description="计划描述")

    price_monthly: Decimal = Field(default=0, ge=0, description="月付价格")
    price_yearly: Decimal = Field(default=0, ge=0, description="年付价格")
    currency: str = Field(default="CNY", max_length=10, description="货币单位")

    max_stores: int = Field(default=1, ge=1, description="最大门店数")
    max_admins: int = Field(default=5, ge=1, description="最大管理员数")
    max_doctors: int = Field(default=50, ge=1, description="最大医生数")
    max_appointments_per_month: int = Field(default=1000, ge=0, description="月预约上限")
    max_storage_mb: int = Field(default=1024, ge=100, description="存储空间上限(MB)")

    features: Optional[str] = Field(None, description="功能开关配置(JSON)")
    is_default: bool = Field(default=False, description="是否为默认计划")


class SubscriptionPlanCreate(SubscriptionPlanBase):
    """创建订阅计划"""
    pass


class SubscriptionPlanUpdate(BaseModel):
    """更新订阅计划"""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price_monthly: Optional[Decimal] = Field(None, ge=0)
    price_yearly: Optional[Decimal] = Field(None, ge=0)
    max_stores: Optional[int] = Field(None, ge=1)
    max_admins: Optional[int] = Field(None, ge=1)
    max_doctors: Optional[int] = Field(None, ge=1)
    max_appointments_per_month: Optional[int] = Field(None, ge=0)
    max_storage_mb: Optional[int] = Field(None, ge=100)
    features: Optional[str] = None
    status: Optional[int] = Field(None, ge=0, le=1)
    is_default: Optional[bool] = None


class SubscriptionPlanResponse(SubscriptionPlanBase):
    """订阅计划响应"""
    id: str
    status: int = Field(..., description="状态: 0-禁用 1-启用")
    sort_order: int = Field(default=0, description="排序")
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )


class SubscriptionPlanListResponse(BaseModel):
    """订阅计划列表响应（简化版）"""
    id: str
    plan_code: str
    name: str
    price_monthly: Decimal
    price_yearly: Decimal
    max_stores: int
    max_admins: int
    max_doctors: int
    max_appointments_per_month: int
    status: int
    is_default: bool
    sort_order: int = 0

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )


# ==================== 租户 ====================

class TenantBase(BaseModel):
    """租户基础 Schema"""
    tenant_code: str = Field(..., max_length=50, pattern=r"^[a-z0-9-]+$", description="租户标识（字母数字和连字符）")
    name: str = Field(..., max_length=100, description="租户名称")
    contact_name: Optional[str] = Field(None, max_length=100, description="联系人姓名")
    contact_phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    contact_email: Optional[str] = Field(None, max_length=100, description="联系邮箱")
    address: Optional[str] = Field(None, max_length=255, description="详细地址")
    custom_domain: Optional[str] = Field(None, max_length=255, description="自定义域名")
    subdomain: Optional[str] = Field(None, max_length=100, description="子域名前缀")

    @field_validator('tenant_code')
    @classmethod
    def validate_tenant_code(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError('租户标识至少3个字符')
        if len(v) > 50:
            raise ValueError('租户标识最多50个字符')
        return v.lower()


class TenantCreate(TenantBase):
    """创建租户"""
    subscription_plan_id: Optional[str] = Field(None, description="订阅计划ID")
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|yearly)$", description="计费周期")
    max_stores: Optional[int] = Field(None, ge=1, description="最大门店数（覆盖计划）")
    max_admins: Optional[int] = Field(None, ge=1, description="最大管理员数（覆盖计划）")
    max_doctors: Optional[int] = Field(None, ge=1, description="最大医生数（覆盖计划）")
    max_appointments_per_month: Optional[int] = Field(None, ge=0, description="月预约上限（覆盖计划）")
    features: Optional[str] = Field(None, description="功能开关(JSON)")
    branding_config: Optional[str] = Field(None, description="品牌配置(JSON)")
    is_trial: bool = Field(default=False, description="是否为试用租户")


class TenantUpdate(BaseModel):
    """更新租户"""
    name: Optional[str] = Field(None, max_length=100)
    contact_name: Optional[str] = Field(None, max_length=100)
    contact_phone: Optional[str] = Field(None, max_length=20)
    contact_email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=255)
    custom_domain: Optional[str] = Field(None, max_length=255)
    subdomain: Optional[str] = Field(None, max_length=100)
    max_stores: Optional[int] = Field(None, ge=1)
    max_admins: Optional[int] = Field(None, ge=1)
    max_doctors: Optional[int] = Field(None, ge=1)
    max_appointments_per_month: Optional[int] = Field(None, ge=0)
    features: Optional[str] = None
    branding_config: Optional[str] = None


class TenantResponse(TenantBase):
    """租户响应"""
    id: str
    status: int = Field(..., description="状态: 0-禁用 1-正常 2-欠费 3-试用")
    subscription_plan_id: Optional[str] = None
    subscription_plan: Optional[SubscriptionPlanListResponse] = None
    subscription_start_at: Optional[datetime] = None
    subscription_end_at: Optional[datetime] = None
    billing_cycle: str = Field(default="monthly")
    max_stores: Optional[int] = None
    max_admins: Optional[int] = None
    max_doctors: Optional[int] = None
    max_appointments_per_month: Optional[int] = None
    features: Optional[str] = None
    branding_config: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    # 计算字段
    is_subscription_active: bool = Field(..., description="订阅是否有效")

    model_config = {"from_attributes": True}


class TenantListResponse(BaseModel):
    """租户列表响应（简化版）"""
    id: str
    tenant_code: str
    name: str
    status: int
    subscription_plan_id: Optional[str] = None
    subscription_plan_name: Optional[str] = None
    subscription_end_at: Optional[datetime] = None
    store_count: int = Field(default=0, description="门店数")
    admin_count: int = Field(default=0, description="管理员数")
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantQuery(BaseModel):
    """租户查询参数"""
    keyword: Optional[str] = None
    status: Optional[int] = None
    subscription_plan_id: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)


# ==================== 租户订阅 ====================

class TenantSubscriptionCreate(BaseModel):
    """创建租户订阅"""
    plan_id: str = Field(..., description="订阅计划ID")
    billing_cycle: str = Field(..., pattern="^(monthly|yearly)$", description="计费周期")
    start_at: Optional[datetime] = Field(None, description="开始时间（默认当前时间）")
    auto_renew: bool = Field(default=False, description="是否自动续费")


class TenantSubscriptionResponse(BaseModel):
    """租户订阅响应"""
    id: str
    tenant_id: str
    plan_id: str
    plan_code: str
    plan_name: str
    billing_cycle: str
    start_at: datetime
    end_at: datetime
    amount: Optional[Decimal] = None
    final_amount: Optional[Decimal] = None
    payment_status: str
    status: int
    auto_renew: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ==================== 租户用量 ====================

class TenantUsageResponse(BaseModel):
    """租户用量响应"""
    tenant_id: str
    usage_date: date

    # 预约统计
    appointment_count: int = 0
    appointment_completed_count: int = 0
    appointment_cancelled_count: int = 0

    # 用户统计
    new_user_count: int = 0
    active_user_count: int = 0

    # 医生统计
    active_doctor_count: int = 0

    # 存储统计
    storage_used_mb: Decimal = Decimal("0")

    # 消息统计
    sms_sent_count: int = 0
    push_sent_count: int = 0

    model_config = {"from_attributes": True}


class TenantUsageSummary(BaseModel):
    """租户用量汇总"""
    tenant_id: str
    tenant_name: str

    # 当前配额
    max_stores: int
    max_admins: int
    max_doctors: int
    max_appointments_per_month: int

    # 当前使用量
    current_store_count: int = 0
    current_admin_count: int = 0
    current_doctor_count: int = 0
    current_month_appointments: int = 0
    current_storage_mb: Decimal = Decimal("0")

    # 使用率
    store_usage_rate: float = Field(..., description="门店使用率(%)")
    admin_usage_rate: float = Field(..., description="管理员使用率(%)")
    doctor_usage_rate: float = Field(..., description="医生使用率(%)")
    appointment_usage_rate: float = Field(..., description="预约使用率(%)")


class TenantUsageQuery(BaseModel):
    """租户用量查询参数"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
