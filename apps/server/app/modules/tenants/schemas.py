"""租户相关的 Pydantic Schema"""
import json
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.base import BaseRequestSchema, BaseSchema
from app.schemas.response import to_camel

# ==================== 密码策略 ====================

class PasswordPolicy(BaseModel):
    """租户密码策略配置"""
    min_length: int = Field(default=6, ge=4, le=32, description="最小长度")
    max_length: int = Field(default=20, ge=8, le=64, description="最大长度")
    require_uppercase: bool = Field(default=False, description="要求大写字母")
    require_lowercase: bool = Field(default=False, description="要求小写字母")
    require_digit: bool = Field(default=False, description="要求数字")
    require_special: bool = Field(default=False, description="要求特殊字符")
    special_chars: str = Field(default="!@#$%^&*", description="允许的特殊字符集")
    disallow_username: bool = Field(default=False, description="禁止包含用户名")
    disallow_phone: bool = Field(default=False, description="禁止包含手机号")
    max_repeated_chars: int = Field(default=0, ge=0, le=10, description="最大允许连续重复字符数（0表示不限制）")
    history_count: int = Field(default=0, ge=0, le=10, description="密码历史检查次数（0表示不检查）")
    expiry_days: int = Field(default=0, ge=0, le=365, description="密码过期天数（0表示不过期）")

    @field_validator("max_length")
    @classmethod
    def validate_max_length(cls, v: int, info) -> int:
        values = info.data
        if "min_length" in values and v < values["min_length"]:
            raise ValueError("max_length 不能小于 min_length")
        return v

    model_config = ConfigDict(extra="ignore")


# ==================== 功能开关 (Features) ====================

# TenantFeatures 已迁移至 app.common.feature_definitions（消除 common -> modules 反向依赖）
# 此处保留 re-export 供 tenants 模块内部使用
from app.common.feature_definitions import TenantFeatures  # noqa: E402, F401


_QUOTA_FIELDS = frozenset({"lowcode_max_pages"})


def _validate_features_json(v: str | None) -> str | None:
    """校验 features 字段：字符串 -> 解析为 TenantFeatures -> 序列化回规范 JSON。

    - None / 空字符串 -> None（合法）
    - 合法 JSON 但值类型不符（非 bool）-> 抛出校验错误
    - 非法 JSON -> 抛出校验错误
    - 校验通过后返回 **规范化的 JSON 字符串**（key 排序，保证幂等）
    """
    if v is None or v.strip() == "":
        return None
    try:
        parsed = json.loads(v)
    except json.JSONDecodeError as exc:
        raise ValueError(f"features 不是合法的 JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("features 必须是一个 JSON 对象 (dict)，例如 {\"basic_appointment\": true}")

    # 用 TenantFeatures 做结构化校验（extra="allow" 保证新字段不报错）
    try:
        features_model = TenantFeatures(**parsed)
    except Exception as exc:
        raise ValueError(f"features 结构校验失败: {exc}") from exc

    # 额外检查：值类型必须合法（bool 或 int，int 仅用于配额字段）
    for key, value in parsed.items():
        if isinstance(value, bool):
            continue
        # 配额字段允许 int 类型
        if isinstance(value, int) and key in _QUOTA_FIELDS:
            continue
        raise ValueError(
            f"features[\"{key}\"] 的值必须是布尔类型 (true/false)，"
            f"当前值: {repr(value)}；配额字段需为整数"
        )

    # 返回规范化 JSON（保留所有字段，包括额外字段）
    return json.dumps(parsed, sort_keys=True, ensure_ascii=False)


# ==================== 订阅计划 ====================

class SubscriptionPlanBase(BaseModel):
    """订阅计划基础 Schema"""
    plan_code: str = Field(..., max_length=50, description="计划编码")
    name: str = Field(..., max_length=100, description="计划名称")
    description: str | None = Field(None, description="计划描述")

    price_monthly: Decimal = Field(default=0, ge=0, description="月付价格")
    price_yearly: Decimal = Field(default=0, ge=0, description="年付价格")
    currency: str = Field(default="CNY", max_length=10, description="货币单位")

    max_stores: int = Field(default=1, ge=1, description="最大门店数")
    max_admins: int = Field(default=5, ge=1, description="最大管理员数")
    max_doctors: int = Field(default=50, ge=1, description="最大医生数")
    max_appointments_per_month: int = Field(default=1000, ge=0, description="月预约上限")
    max_storage_mb: int = Field(default=1024, ge=100, description="存储空间上限(MB)")
    max_lowcode_pages: int = Field(default=5, ge=0, description="最大低代码页面数")
    max_miniapp_instances: int = Field(default=3, ge=0, description="最大小程序实例数")

    features: str | None = Field(None, description="功能开关配置(JSON)")
    is_default: bool = Field(default=False, description="是否为默认计划")

    @field_validator("features")
    @classmethod
    def validate_features(cls, v: str | None) -> str | None:
        return _validate_features_json(v)


class SubscriptionPlanCreate(SubscriptionPlanBase):
    """创建订阅计划"""
    pass


class SubscriptionPlanUpdate(BaseModel):
    """更新订阅计划"""
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    price_monthly: Decimal | None = Field(None, ge=0)
    price_yearly: Decimal | None = Field(None, ge=0)
    max_stores: int | None = Field(None, ge=1)
    max_admins: int | None = Field(None, ge=1)
    max_doctors: int | None = Field(None, ge=1)
    max_appointments_per_month: int | None = Field(None, ge=0)
    max_storage_mb: int | None = Field(None, ge=100)
    max_lowcode_pages: int | None = Field(None, ge=0)
    max_miniapp_instances: int | None = Field(None, ge=0)
    features: str | None = None
    status: int | None = Field(None, ge=0, le=1)
    is_default: bool | None = None

    @field_validator("features")
    @classmethod
    def validate_features(cls, v: str | None) -> str | None:
        return _validate_features_json(v)


class SubscriptionPlanResponse(SubscriptionPlanBase, BaseSchema):
    """订阅计划响应"""
    id: str
    status: int = Field(..., description="状态: 0-禁用 1-启用")
    sort_order: int = Field(default=0, description="排序")
    created_at: datetime
    updated_at: datetime | None = None


class SubscriptionPlanListResponse(BaseSchema):
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


# ==================== 租户 ====================

class TenantBase(BaseModel):
    """租户基础 Schema"""
    tenant_code: str = Field(..., max_length=50, pattern=r"^[a-z0-9-]+$", description="租户标识（字母数字和连字符）")
    name: str = Field(..., max_length=100, description="租户名称")
    contact_name: str | None = Field(None, max_length=100, description="联系人姓名")
    contact_phone: str | None = Field(None, max_length=20, description="联系电话")
    contact_email: str | None = Field(None, max_length=100, description="联系邮箱")
    address: str | None = Field(None, max_length=255, description="详细地址")
    custom_domain: str | None = Field(None, max_length=255, description="自定义域名")
    subdomain: str | None = Field(None, max_length=100, description="子域名前缀")

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
    subscription_plan_id: str | None = Field(None, description="订阅计划ID")
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|yearly)$", description="计费周期")
    max_stores: int | None = Field(None, ge=1, description="最大门店数（覆盖计划）")
    max_admins: int | None = Field(None, ge=1, description="最大管理员数（覆盖计划）")
    max_doctors: int | None = Field(None, ge=1, description="最大医生数（覆盖计划）")
    max_appointments_per_month: int | None = Field(None, ge=0, description="月预约上限（覆盖计划）")
    max_lowcode_pages: int | None = Field(None, ge=0, description="最大低代码页面数（覆盖计划）")
    max_miniapp_instances: int | None = Field(None, ge=0, description="最大小程序实例数（覆盖计划）")
    features: str | None = Field(None, description="功能开关(JSON)")
    branding_config: str | None = Field(None, description="品牌配置(JSON)")
    password_policy: str | None = Field(None, description="密码策略(JSON)")
    tags: str | None = Field(None, description="租户标签(JSON数组)")
    log_retention_days: int | None = Field(None, ge=7, le=365, description="日志保留天数")
    is_trial: bool = Field(default=False, description="是否为试用租户")

    @field_validator("features")
    @classmethod
    def validate_features(cls, v: str | None) -> str | None:
        return _validate_features_json(v)

    @field_validator("password_policy")
    @classmethod
    def validate_password_policy(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        try:
            parsed = json.loads(v)
        except json.JSONDecodeError as exc:
            raise ValueError(f"password_policy 不是合法的 JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("password_policy 必须是一个 JSON 对象")
        try:
            PasswordPolicy(**parsed)
        except Exception as exc:
            raise ValueError(f"password_policy 结构校验失败: {exc}") from exc
        return json.dumps(parsed, sort_keys=True, ensure_ascii=False)


class TenantUpdate(BaseModel):
    """更新租户（平台管理员）"""
    name: str | None = Field(None, max_length=100)
    contact_name: str | None = Field(None, max_length=100)
    contact_phone: str | None = Field(None, max_length=20)
    contact_email: str | None = Field(None, max_length=100)
    address: str | None = Field(None, max_length=255)
    custom_domain: str | None = Field(None, max_length=255)
    subdomain: str | None = Field(None, max_length=100)
    max_stores: int | None = Field(None, ge=1)
    max_admins: int | None = Field(None, ge=1)
    max_doctors: int | None = Field(None, ge=1)
    max_appointments_per_month: int | None = Field(None, ge=0)
    max_lowcode_pages: int | None = Field(None, ge=0)
    max_miniapp_instances: int | None = Field(None, ge=0)
    features: str | None = None
    branding_config: str | None = None
    password_policy: str | None = None
    tags: str | None = None
    log_retention_days: int | None = Field(None, ge=7, le=365, description="日志保留天数")
    rate_limit_per_minute: int | None = Field(None, ge=1, le=10000, description="每分钟请求上限")
    rate_limit_per_second: int | None = Field(None, ge=1, le=1000, description="每秒请求上限")

    model_config = ConfigDict(extra="forbid")

    @field_validator("features")
    @classmethod
    def validate_features(cls, v: str | None) -> str | None:
        return _validate_features_json(v)

    @field_validator("password_policy")
    @classmethod
    def validate_password_policy(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        try:
            parsed = json.loads(v)
        except json.JSONDecodeError as exc:
            raise ValueError(f"password_policy 不是合法的 JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("password_policy 必须是一个 JSON 对象")
        try:
            PasswordPolicy(**parsed)
        except Exception as exc:
            raise ValueError(f"password_policy 结构校验失败: {exc}") from exc
        return json.dumps(parsed, sort_keys=True, ensure_ascii=False)


class TenantSelfUpdateRequest(BaseModel):
    """租户管理员自助更新（仅允许修改自身基本信息和品牌配置）"""
    name: str | None = Field(None, max_length=100)
    contact_name: str | None = Field(None, max_length=100)
    contact_phone: str | None = Field(None, max_length=20)
    contact_email: str | None = Field(None, max_length=100)
    address: str | None = Field(None, max_length=255)
    branding_config: str | None = None

    model_config = ConfigDict(extra="forbid")


class TenantResponse(TenantBase):
    """租户响应"""
    id: str
    status: int = Field(..., description="状态: 0-禁用 1-正常 2-欠费 3-试用")
    subscription_plan_id: str | None = None
    subscription_plan: SubscriptionPlanListResponse | None = None
    subscription_start_at: datetime | None = None
    subscription_end_at: datetime | None = None
    billing_cycle: str = Field(default="monthly")
    max_stores: int | None = None
    max_admins: int | None = None
    max_doctors: int | None = None
    max_appointments_per_month: int | None = None
    max_lowcode_pages: int | None = None
    max_miniapp_instances: int | None = None
    features: str | None = None
    branding_config: str | None = None
    password_policy: str | None = None
    rate_limit_per_minute: int | None = Field(None, description="每分钟请求上限（覆盖全局 300）")
    rate_limit_per_second: int | None = Field(None, description="每秒请求上限（覆盖全局 50）")
    tags: str | None = None
    log_retention_days: int | None = 90
    created_at: datetime
    updated_at: datetime | None = None

    # 计算字段
    is_subscription_active: bool = Field(default=False, description="订阅是否有效")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )


class TenantListResponse(BaseModel):
    """租户列表响应（简化版）"""
    id: str
    tenant_code: str
    name: str
    status: int
    subscription_plan_id: str | None = None
    subscription_plan_name: str | None = None
    subscription_end_at: datetime | None = None
    store_count: int = Field(default=0, description="门店数")
    admin_count: int = Field(default=0, description="管理员数")
    created_at: datetime
    tags: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )


class TenantQuery(BaseModel):
    """租户查询参数"""
    keyword: str | None = None
    status: int | None = None
    subscription_plan_id: str | None = None
    tags: str | None = Field(None, description="标签筛选(逗号分隔)")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)


# ==================== 租户订阅 ====================

class TenantSubscriptionCreate(BaseModel):
    """创建租户订阅"""
    plan_id: str = Field(..., description="订阅计划ID")
    billing_cycle: str = Field(..., pattern="^(monthly|yearly)$", description="计费周期")
    start_at: datetime | None = Field(None, description="开始时间（默认当前时间）")
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
    amount: Decimal | None = None
    final_amount: Decimal | None = None
    payment_status: str
    status: int
    auto_renew: bool
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )


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

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )


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
    start_date: date | None = None
    end_date: date | None = None


class UsageTrendItem(BaseModel):
    """用量趋势单项"""
    period: str = Field(..., description="周期标识，如 2026-W17 或 2026-04")
    appointment_count: int = 0
    new_user_count: int = 0
    active_user_count: int = 0
    sms_sent_count: int = 0
    push_sent_count: int = 0
    storage_used_mb: Decimal = Decimal("0")

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )


class TenantUsageTrends(BaseModel):
    """租户用量趋势响应"""
    tenant_id: str
    period_type: str = Field(..., description="周期类型: week / month")
    current_period: UsageTrendItem | None = None
    previous_period: UsageTrendItem | None = None
    trends: list[UsageTrendItem] = []

    # 同比/环比变化率（百分比）
    appointment_change_rate: float | None = Field(None, description="预约量环比变化率(%)")
    new_user_change_rate: float | None = Field(None, description="新用户环比变化率(%)")
    active_user_change_rate: float | None = Field(None, description="活跃用户环比变化率(%)")

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )


# ==================== 当前租户信息（admin + 患者端） ====================

class CurrentTenantResponse(BaseModel):
    """当前租户精简信息（admin 用 /tenants/me）"""
    id: str
    tenant_code: str = Field(..., serialization_alias="tenantCode")
    name: str
    status: int
    subscription_plan_name: str | None = Field(None, serialization_alias="subscriptionPlanName")
    subscription_end_at: datetime | None = Field(None, serialization_alias="subscriptionEndAt")
    is_subscription_active: bool = Field(False, serialization_alias="isSubscriptionActive")
    days_until_expiry: int | None = Field(None, serialization_alias="daysUntilExpiry")
    billing_cycle: str = Field(default="monthly", serialization_alias="billingCycle")
    contact_phone: str | None = Field(None, serialization_alias="contactPhone")
    branding_config: dict | None = Field(None, serialization_alias="brandingConfig")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class CurrentTenantPublicResponse(BaseModel):
    """当前租户公开信息（患者端匿名可访问 /tenants/me/public）"""
    status: int
    subscription_end_at: datetime | None = Field(None, serialization_alias="subscriptionEndAt")
    is_subscription_active: bool = Field(False, serialization_alias="isSubscriptionActive")
    name: str | None = None
    branding_config: dict | None = Field(None, serialization_alias="brandingConfig")
    branding_config: dict | None = Field(None, serialization_alias="brandingConfig")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


class TenantNotificationResponse(BaseModel):
    """租户通知"""
    id: str
    notification_type: str = Field(..., serialization_alias="notificationType")
    title: str
    content: str
    is_read: bool = Field(False, serialization_alias="isRead")
    read_at: datetime | None = Field(None, serialization_alias="readAt")
    priority: int = 0
    extra_metadata: str | None = Field(None, serialization_alias="extraMetadata")
    created_at: datetime = Field(..., serialization_alias="createdAt")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )


class TenantNotificationListResponse(BaseModel):
    """通知列表 + 未读数"""
    items: list[TenantNotificationResponse]
    unread_count: int = Field(0, serialization_alias="unreadCount")
    total: int = 0

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


# ==================== 跨租户数据迁移 ====================

class TenantMigrateRequest(BaseModel):
    """跨租户数据迁移请求"""
    source_tenant_id: str = Field(..., description="源租户ID")
    preserve_ids: bool = Field(default=False, description="是否保留原始ID")
    entity_types: list[str] | None = Field(
        default=None,
        description="要迁移的实体类型列表，None表示全部"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )


class TenantMigrateResponse(BaseModel):
    """跨租户数据迁移响应"""
    target_tenant_id: str = Field(..., serialization_alias="targetTenantId")
    source_tenant_id: str = Field(..., serialization_alias="sourceTenantId")
    duration_ms: int = Field(..., serialization_alias="durationMs")
    copied: dict = Field(default_factory=dict, description="各实体类型成功复制数量")
    failures: list[dict] = Field(default_factory=list, description="失败记录列表")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


# ==================== 租户管理员仪表板 ====================

class TenantDashboardResponse(BaseModel):
    """租户管理员仪表板"""
    tenant_id: str
    tenant_name: str
    status: int
    plan_name: str | None = None
    subscription_end_at: datetime | None = None
    is_subscription_active: bool = False
    days_until_expiry: int | None = None

    store_usage: dict = Field(default_factory=dict)
    admin_usage: dict = Field(default_factory=dict)
    doctor_usage: dict = Field(default_factory=dict)
    appointment_usage: dict = Field(default_factory=dict)

    today_appointments: int = 0
    today_new_users: int = 0
    active_doctors: int = 0

    alerts: list[dict] = Field(default_factory=list)

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )


# ==================== 租户自助注册 ====================

class TenantSelfRegisterRequest(BaseModel):
    """租户自助注册请求"""
    tenant_code: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-z0-9-]+$")
    name: str = Field(..., min_length=2, max_length=100)
    contact_name: str = Field(..., min_length=2, max_length=100)
    contact_phone: str = Field(..., min_length=11, max_length=20)
    contact_email: str | None = Field(None, max_length=100)
    admin_username: str = Field(..., min_length=2, max_length=50)
    admin_password: str = Field(..., min_length=6, max_length=20)
    captcha_token: str | None = Field(None, max_length=500, description="人机验证 token（预留，对接第三方 captcha 服务）")
    source: str | None = Field(None, max_length=50, description="注册来源（如 website, miniapp）")
    referral_code: str | None = Field(None, max_length=50, description="推荐码")

    @field_validator("admin_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """注册密码需满足 PasswordPolicy 默认策略（单一事实来源）"""
        from app.modules.tenants.password_policy import (
            DEFAULT_POLICY,
            PasswordPolicyValidator,
        )

        is_valid, errors = PasswordPolicyValidator(dict(DEFAULT_POLICY)).validate(v)
        if not is_valid:
            raise ValueError("; ".join(errors))
        return v

    @field_validator("captcha_token")
    @classmethod
    def validate_captcha_token(cls, v: str | None) -> str | None:
        """captcha_token 占位校验——接入第三方服务时替换此逻辑"""
        return v

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )


class TenantSelfRegisterResponse(BaseModel):
    """租户自助注册响应"""
    tenant_id: str
    tenant_code: str
    name: str
    admin_id: str
    message: str = "注册成功，试用期已激活"

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )


# ==================== 迁移前预检 ====================

class TenantMigratePrecheckRequest(BaseModel):
    """迁移前预检请求"""
    source_tenant_id: str = Field(..., description="源租户ID")
    entity_types: list[str] | None = Field(default=None, description="要迁移的实体类型列表")

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )


class PrecheckQuotaItem(BaseModel):
    """预检配额项"""
    resource_name: str
    current_count: int
    max_count: int
    source_count: int
    would_exceed: bool

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )


class TenantMigratePrecheckResponse(BaseModel):
    """迁移前预检响应"""
    can_migrate: bool = Field(..., serialization_alias="canMigrate")
    warnings: list[str] = Field(default_factory=list)
    quota_checks: list[PrecheckQuotaItem] = Field(default_factory=list)
    entity_counts: dict = Field(default_factory=dict)
    estimated_duration_ms: int = Field(default=0, serialization_alias="estimatedDurationMs")

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )


# ==================== 租户标签 ====================

class TenantTagsUpdate(BaseModel):
    """租户标签更新"""
    tags: list[str] = Field(..., description="标签列表")

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )
