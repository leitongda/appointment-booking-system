from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, time
from app.core.config import settings
from app.schemas.response import to_camel

class StoreBase(BaseModel):
    """门店基础模型"""
    model_config = ConfigDict(
        populate_by_name=True,  # 允许通过字段名或别名填充
        alias_generator=to_camel,  # 自动生成 camelCase 别名
    )
    
    name: str = Field(..., max_length=100, description="门店名称")
    code: Optional[str] = Field(None, max_length=50, description="门店编码")
    address: Optional[str] = Field(None, max_length=255, description="详细地址")
    province: Optional[str] = Field(None, max_length=50, description="省份")
    city: Optional[str] = Field(None, max_length=50, description="城市")
    district: Optional[str] = Field(None, max_length=50, description="区县")
    latitude: Optional[str] = Field(None, max_length=20, description="纬度")
    longitude: Optional[str] = Field(None, max_length=20, description="经度")
    phone: Optional[str] = Field(None, max_length=50, description="联系电话")
    contact_person: Optional[str] = Field(None, max_length=50, description="联系人")
    description: Optional[str] = Field(None, description="门店简介")
    opening_time: Optional[time] = Field(None, description="营业开始时间")
    closing_time: Optional[time] = Field(None, description="营业结束时间")
    working_days: Optional[str] = Field("1,2,3,4,5,6,7", description="工作日")
    image: Optional[str] = Field(None, max_length=255, description="门店图片")
    logo: Optional[str] = Field(None, max_length=255, description="门店logo")
    password: Optional[str] = Field(None, max_length=100, description="门店密码（明文，服务端自动哈希）")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    theme_style: Optional[str] = Field(None, max_length=50, description="风格选择")
    sort_order: int = Field(0, ge=0, description="排序")
    status: int = Field(1, ge=0, le=2, description="状态: 0-停业 1-营业 2-禁用")
    max_cards_per_user: int = Field(5, ge=1, le=20, description="每用户可建就诊卡数量上限")

class StoreCreate(StoreBase):
    """创建门店"""
    pass

class StoreUpdate(BaseModel):
    """更新门店"""
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )
    
    name: Optional[str] = Field(None, max_length=100, description="门店名称")
    code: Optional[str] = Field(None, max_length=50, description="门店编码")
    address: Optional[str] = Field(None, max_length=255, description="详细地址")
    province: Optional[str] = Field(None, max_length=50, description="省份")
    city: Optional[str] = Field(None, max_length=50, description="城市")
    district: Optional[str] = Field(None, max_length=50, description="区县")
    latitude: Optional[str] = Field(None, max_length=20, description="纬度")
    longitude: Optional[str] = Field(None, max_length=20, description="经度")
    phone: Optional[str] = Field(None, max_length=50, description="联系电话")
    contact_person: Optional[str] = Field(None, max_length=50, description="联系人")
    description: Optional[str] = Field(None, description="门店简介")
    opening_time: Optional[time] = Field(None, description="营业开始时间")
    closing_time: Optional[time] = Field(None, description="营业结束时间")
    working_days: Optional[str] = Field(None, description="工作日")
    image: Optional[str] = Field(None, max_length=255, description="门店图片")
    logo: Optional[str] = Field(None, max_length=255, description="门店logo")
    password: Optional[str] = Field(None, max_length=100, description="门店密码（明文，服务端自动哈希）")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    theme_style: Optional[str] = Field(None, max_length=50, description="风格选择")
    sort_order: Optional[int] = Field(None, ge=0, description="排序")
    status: Optional[int] = Field(None, ge=0, le=2, description="状态: 0停业 1营业 2禁用")
    max_cards_per_user: Optional[int] = Field(None, ge=1, le=20, description="每用户可建就诊卡数量上限")

class StoreResponse(StoreBase):
    """门店响应"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,  # 序列化时使用别名 (camelCase)
    )
    
    id: str = Field(..., description="门店ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    # 排除密码字段，不返回给前端
    password: Optional[str] = Field(None, exclude=True)

class StoreListResponse(BaseModel):
    """门店列表响应"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )
    
    id: str = Field(..., description="门店ID")
    name: str = Field(..., description="门店名称")
    code: Optional[str] = Field(None, description="门店编码")
    address: Optional[str] = Field(None, description="详细地址")
    phone: Optional[str] = Field(None, description="联系电话")
    logo: Optional[str] = Field(None, description="门店logo")
    theme_style: Optional[str] = Field(None, description="风格选择")
    status: int = Field(..., description="状态: 0停业 1营业 2禁用")
    department_count: int = Field(0, description="科室数量")
    max_cards_per_user: int = Field(5, description="每用户可建就诊卡数量上限")
    created_at: datetime = Field(..., description="创建时间")

class StoreInfo(BaseModel):
    """门店简要信息（用于登录响应等场景）"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )
    
    id: str = Field(..., description="门店ID")
    name: str = Field(..., description="门店名称")
    logo: Optional[str] = Field(None, description="门店logo")
    theme_style: Optional[str] = Field(None, description="风格选择")

class StoreQuery(BaseModel):
    """门店查询参数"""
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )
    
    keyword: Optional[str] = Field(None, description="搜索关键词")
    status: Optional[int] = Field(None, description="状态筛选")
    city: Optional[str] = Field(None, description="城市筛选")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量")

class StoreWechatConfigUpdate(BaseModel):
    """更新门店微信配置"""
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )
    
    app_id: Optional[str] = Field(None, max_length=100, description="小程序AppID")
    app_secret: Optional[str] = Field(None, max_length=100, description="小程序Secret")
    mch_id: Optional[str] = Field(None, max_length=100, description="商户号")
    api_key: Optional[str] = Field(None, max_length=100, description="API密钥")
    notify_url: Optional[str] = Field(None, max_length=255, description="支付回调地址")

class StoreWechatConfigResponse(BaseModel):
    """门店微信配置响应"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )
    
    app_id: Optional[str] = Field(None, description="小程序AppID")
    app_secret: Optional[str] = Field(None, description="小程序Secret（掩码）")
    mch_id: Optional[str] = Field(None, description="商户号")
    api_key: Optional[str] = Field(None, description="API密钥（掩码）")
    notify_url: Optional[str] = Field(None, description="支付回调地址")
