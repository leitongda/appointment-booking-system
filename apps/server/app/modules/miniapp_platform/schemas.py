from app.schemas.response import to_camel

"""小程序平台相关的 Pydantic Schema"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ==================== Company (公司/结算主体) ====================

class CompanyBase(BaseModel):
    """公司基础 Schema"""
    name: str = Field(..., max_length=100, description="公司主体名称")
    code: str | None = Field(None, max_length=50, description="主体编码，租户内唯一")
    unified_social_credit_code: str | None = Field(None, max_length=50, description="统一社会信用代码")
    contact_name: str | None = Field(None, max_length=100, description="联系人")
    contact_phone: str | None = Field(None, max_length=20, description="联系电话")

class CompanyCreate(CompanyBase):
    """创建公司"""
    pass

class CompanyUpdate(BaseModel):
    """更新公司"""
    name: str | None = Field(None, max_length=100)
    code: str | None = Field(None, max_length=50)
    unified_social_credit_code: str | None = Field(None, max_length=50)
    contact_name: str | None = Field(None, max_length=100)
    contact_phone: str | None = Field(None, max_length=20)
    status: int | None = Field(None, ge=0, le=1)

class CompanyResponse(CompanyBase):
    """公司响应"""
    id: str
    status: int = Field(..., description="状态: 0-禁用 1-启用")
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )

class CompanyListResponse(BaseModel):
    """公司列表响应（简化版）"""
    id: str
    name: str
    code: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    status: int
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )

# ==================== PaymentProfile (支付配置) ====================

class PaymentProfileBase(BaseModel):
    """支付配置基础 Schema"""
    name: str = Field(..., max_length=100, description="支付配置名称")
    code: str | None = Field(None, max_length=50, description="支付配置编码，租户内唯一")
    mode: str = Field(default="direct", max_length=30, description="支付模式: direct/service_provider")
    app_id: str | None = Field(None, max_length=100, description="支付关联AppID")
    mch_id: str | None = Field(None, max_length=100, description="直连商户号")
    sub_mchid: str | None = Field(None, max_length=100, description="服务商模式子商户号")
    notify_url: str | None = Field(None, max_length=255, description="支付回调地址")
    refund_notify_url: str | None = Field(None, max_length=255, description="退款回调地址")
    api_v3_key_ref: str | None = Field(None, max_length=255, description="APIv3 Key引用，如 env:WX_API_V3_KEY")
    cert_serial_no: str | None = Field(None, max_length=100, description="商户证书序列号")
    private_key_ref: str | None = Field(None, max_length=255, description="商户私钥引用")
    company_id: str | None = Field(None, description="公司主体ID")

    @field_validator('mode')
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in ['direct', 'service_provider']:
            raise ValueError('支付模式必须是 direct 或 service_provider')
        return v

class PaymentProfileCreate(PaymentProfileBase):
    """创建支付配置"""
    pass

class PaymentProfileUpdate(BaseModel):
    """更新支付配置"""
    name: str | None = Field(None, max_length=100)
    code: str | None = Field(None, max_length=50)
    mode: str | None = Field(None, max_length=30)
    app_id: str | None = Field(None, max_length=100)
    mch_id: str | None = Field(None, max_length=100)
    sub_mchid: str | None = Field(None, max_length=100)
    notify_url: str | None = Field(None, max_length=255)
    refund_notify_url: str | None = Field(None, max_length=255)
    api_v3_key_ref: str | None = Field(None, max_length=255)
    cert_serial_no: str | None = Field(None, max_length=100)
    private_key_ref: str | None = Field(None, max_length=255)
    company_id: str | None = None
    is_default: bool | None = None
    status: int | None = Field(None, ge=0, le=1)

class PaymentProfileResponse(PaymentProfileBase):
    """支付配置响应"""
    id: str
    is_default: bool = Field(..., description="是否租户默认支付配置")
    status: int = Field(..., description="状态: 0-禁用 1-启用")
    created_at: datetime
    updated_at: datetime | None = None

    # 关联公司（简化版）
    company: CompanyListResponse | None = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )

class PaymentProfileListResponse(BaseModel):
    """支付配置列表响应（简化版）"""
    id: str
    name: str
    code: str | None = None
    mode: str
    app_id: str | None = None
    is_default: bool
    status: int
    company_name: str | None = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )

class PaymentProfileQuery(BaseModel):
    """支付配置查询参数"""
    keyword: str | None = None
    status: int | None = None
    company_id: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)

# ==================== MiniappInstance (小程序实例) ====================

class MiniappInstanceBase(BaseModel):
    """小程序实例基础 Schema"""
    code: str | None = Field(None, max_length=50, description="实例编码，租户内唯一")
    name: str = Field(..., max_length=100, description="实例名称")
    app_id: str = Field(..., max_length=100, description="微信小程序AppID")
    app_secret_ref: str | None = Field(None, max_length=255, description="小程序Secret引用，如 env:WX_APP_SECRET")
    upload_private_key_ref: str | None = Field(None, max_length=255, description="上传私钥引用")
    template_id: str | None = Field(None, description="模板ID")
    template_version_id: str | None = Field(None, description="当前模板版本ID")

class MiniappInstanceCreate(MiniappInstanceBase):
    """创建小程序实例"""
    default_store_id: str | None = Field(None, description="默认门店ID")
    default_payment_profile_id: str | None = Field(None, description="默认支付配置ID")
    app_config: str | None = Field(None, description="实例扩展配置(JSON)")

class MiniappInstanceUpdate(BaseModel):
    """更新小程序实例"""
    code: str | None = Field(None, max_length=50)
    name: str | None = Field(None, max_length=100)
    app_id: str | None = Field(None, max_length=100)
    app_secret_ref: str | None = Field(None, max_length=255)
    upload_private_key_ref: str | None = Field(None, max_length=255)
    template_id: str | None = Field(None)
    template_version_id: str | None = Field(None)
    default_store_id: str | None = Field(None)
    default_payment_profile_id: str | None = Field(None)
    app_config: str | None = Field(None)
    status: int | None = Field(None, ge=0, le=2)

class MiniappInstanceResponse(MiniappInstanceBase):
    """小程序实例响应"""
    id: str
    status: int = Field(..., description="状态: 0-禁用 1-启用 2-归档")
    created_at: datetime
    updated_at: datetime | None = None

    # 关联信息
    template: dict | None = Field(None, description="模板信息")
    template_version: dict | None = Field(None, description="模板版本信息")
    default_store: dict | None = Field(None, description="默认门店信息")
    default_payment_profile: PaymentProfileListResponse | None = Field(None, description="默认支付配置")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )

class MiniappInstanceListResponse(BaseModel):
    """小程序实例列表响应（简化版）"""
    id: str
    code: str | None = None
    name: str
    app_id: str
    status: int
    template_name: str | None = None
    template_version: str | None = None
    store_name: str | None = None
    payment_profile_name: str | None = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )

class MiniappInstanceQuery(BaseModel):
    """小程序实例查询参数"""
    keyword: str | None = None
    status: int | None = None
    template_id: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
