from datetime import datetime, time

from pydantic import ConfigDict, Field

from app.core.config import settings
from app.schemas.base import BaseRequestSchema, BaseSchema
from app.schemas.response import to_camel


class StoreBase(BaseRequestSchema):
    """门店基础模型"""

    name: str = Field(..., max_length=100, description="门店名称")
    code: str | None = Field(None, max_length=50, description="门店编码")
    address: str | None = Field(None, max_length=255, description="详细地址")
    province: str | None = Field(None, max_length=50, description="省份")
    city: str | None = Field(None, max_length=50, description="城市")
    district: str | None = Field(None, max_length=50, description="区县")
    latitude: float | None = Field(None, description="纬度")
    longitude: float | None = Field(None, description="经度")
    phone: str | None = Field(None, max_length=50, description="联系电话")
    contact_person: str | None = Field(None, max_length=50, description="联系人")
    description: str | None = Field(None, description="门店简介")
    opening_time: time | None = Field(None, description="营业开始时间")
    closing_time: time | None = Field(None, description="营业结束时间")
    working_days: str | None = Field("1,2,3,4,5,6,7", description="工作日")
    image: str | None = Field(None, max_length=255, description="门店图片")
    logo: str | None = Field(None, max_length=255, description="门店logo")
    password: str | None = Field(None, max_length=100, description="门店密码（明文，服务端自动哈希）")
    email: str | None = Field(None, max_length=100, description="邮箱")
    theme_style: str | None = Field(None, max_length=50, description="风格选择")
    sort_order: int = Field(0, ge=0, description="排序")
    status: int = Field(1, ge=0, le=2, description="状态: 0-停业 1-营业 2-禁用")
    max_cards_per_user: int = Field(5, ge=1, le=20, description="每用户可建就诊卡数量上限")

class StoreCreate(StoreBase):
    """创建门店"""
    pass

class StoreUpdate(BaseRequestSchema):
    """更新门店"""

    name: str | None = Field(None, max_length=100, description="门店名称")
    code: str | None = Field(None, max_length=50, description="门店编码")
    address: str | None = Field(None, max_length=255, description="详细地址")
    province: str | None = Field(None, max_length=50, description="省份")
    city: str | None = Field(None, max_length=50, description="城市")
    district: str | None = Field(None, max_length=50, description="区县")
    latitude: float | None = Field(None, description="纬度")
    longitude: float | None = Field(None, description="经度")
    phone: str | None = Field(None, max_length=50, description="联系电话")
    contact_person: str | None = Field(None, max_length=50, description="联系人")
    description: str | None = Field(None, description="门店简介")
    opening_time: time | None = Field(None, description="营业开始时间")
    closing_time: time | None = Field(None, description="营业结束时间")
    working_days: str | None = Field(None, description="工作日")
    image: str | None = Field(None, max_length=255, description="门店图片")
    logo: str | None = Field(None, max_length=255, description="门店logo")
    password: str | None = Field(None, max_length=100, description="门店密码（明文，服务端自动哈希）")
    email: str | None = Field(None, max_length=100, description="邮箱")
    theme_style: str | None = Field(None, max_length=50, description="风格选择")
    sort_order: int | None = Field(None, ge=0, description="排序")
    status: int | None = Field(None, ge=0, le=2, description="状态: 0停业 1营业 2禁用")
    max_cards_per_user: int | None = Field(None, ge=1, le=20, description="每用户可建就诊卡数量上限")

class StoreResponse(StoreBase):
    """门店响应
    NOTE: 继承自 StoreBase（现 BaseRequestSchema，2-field 配置），本类有 4-field model_config 覆盖父类配置。
    若改 BaseSchema 会丢掉 StoreBase 继承字段，故保留手写 model_config。
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,  # 序列化时使用别名 (camelCase)
    )

    id: str = Field(..., description="门店ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    # 排除密码字段，不返回给前端
    password: str | None = Field(None, exclude=True)

class StoreListResponse(BaseSchema):
    """门店列表响应"""

    id: str = Field(..., description="门店ID")
    name: str = Field(..., description="门店名称")
    code: str | None = Field(None, description="门店编码")
    address: str | None = Field(None, description="详细地址")
    phone: str | None = Field(None, description="联系电话")
    logo: str | None = Field(None, description="门店logo")
    theme_style: str | None = Field(None, description="风格选择")
    status: int = Field(..., description="状态: 0停业 1营业 2禁用")
    department_count: int = Field(0, description="科室数量")
    max_cards_per_user: int = Field(5, description="每用户可建就诊卡数量上限")
    created_at: datetime = Field(..., description="创建时间")

class StoreInfo(BaseSchema):
    """门店简要信息（用于登录响应等场景）"""

    id: str = Field(..., description="门店ID")
    name: str = Field(..., description="门店名称")
    logo: str | None = Field(None, description="门店logo")
    theme_style: str | None = Field(None, description="风格选择")

class StoreQuery(BaseRequestSchema):
    """门店查询参数"""

    keyword: str | None = Field(None, description="搜索关键词")
    status: int | None = Field(None, description="状态筛选")
    city: str | None = Field(None, description="城市筛选")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量")

class StoreWechatConfigUpdate(BaseRequestSchema):
    """更新门店微信配置"""

    app_id: str | None = Field(None, max_length=100, description="小程序AppID")
    app_secret: str | None = Field(None, max_length=100, description="小程序Secret")
    mch_id: str | None = Field(None, max_length=100, description="商户号")
    api_key: str | None = Field(None, max_length=100, description="API密钥")
    notify_url: str | None = Field(None, max_length=255, description="支付回调地址")

class StoreWechatConfigResponse(BaseSchema):
    """门店微信配置响应"""

    app_id: str | None = Field(None, description="小程序AppID")
    app_secret: str | None = Field(None, description="小程序Secret（掩码）")
    mch_id: str | None = Field(None, description="商户号")
    api_key: str | None = Field(None, description="API密钥（掩码）")
    notify_url: str | None = Field(None, description="支付回调地址")
