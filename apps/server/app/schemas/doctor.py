from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class DoctorBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    # 基础信息
    store_id: Optional[str] = Field(None, description="所属门店ID")
    department_id: str = Field(..., description="科室ID")
    name: str = Field(..., max_length=50, description="医生姓名")
    username: Optional[str] = Field(None, max_length=50, description="医生登录账号")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    gender: int = Field(0, ge=0, le=2, description="性别 0未知 1男 2女")
    avatar: Optional[str] = Field(None, description="头像URL")
    banner: Optional[str] = Field(None, description="医生banner图URL")
    title: Optional[str] = Field(None, max_length=50, description="职称")
    years_of_experience: int = Field(0, ge=0, description="医龄(年)")
    
    # 资质信息
    education: Optional[str] = Field(None, max_length=50, description="学历")
    graduate_school: Optional[str] = Field(None, max_length=100, description="毕业院校")
    license_number: Optional[str] = Field(None, max_length=100, description="执业证书编号")
    license_image: Optional[str] = Field(None, description="执业证书图片URL")
    honors: Optional[str] = Field(None, description="所获荣誉")
    
    # 坐诊设置
    schedule_desc: Optional[str] = Field(None, max_length=255, description="坐诊时间说明")
    max_daily_appointments: int = Field(0, ge=0, description="每日最大接诊量,0表示不限制")
    online_consult_enabled: int = Field(0, ge=0, le=1, description="是否支持在线问诊 0否 1是")
    online_consult_fee: Decimal = Field(Decimal("0"), ge=0, description="在线问诊费用")
    
    # 展示设置
    page_style: int = Field(1, ge=1, le=3, description="页面风格 1/2/3")
    promo_video: Optional[str] = Field(None, description="宣传视频URL")
    tags: Optional[str] = Field(None, max_length=255, description="标签,逗号分隔")
    specialty: Optional[str] = Field(None, description="擅长")
    introduction: Optional[str] = Field(None, description="简介")
    
    # 其他设置
    is_recommended: int = Field(0, ge=0, le=1, description="是否推荐")
    sort_order: int = Field(0, ge=0, description="排序")
    status: int = Field(1, ge=0, le=1, description="状态")
    
    # 诊费设置
    use_fee_template: int = Field(0, ge=0, le=1, description="是否使用诊费模板 0否 1是")

class DoctorCreate(DoctorBase):
    password: Optional[str] = Field(None, min_length=6, description="医生账号密码")

class DoctorUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    # 基础信息
    store_id: Optional[str] = None
    department_id: Optional[str] = None
    name: Optional[str] = Field(None, max_length=50)
    username: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    gender: Optional[int] = Field(None, ge=0, le=2)
    avatar: Optional[str] = None
    banner: Optional[str] = None
    title: Optional[str] = Field(None, max_length=50)
    years_of_experience: Optional[int] = Field(None, ge=0)
    
    # 资质信息
    education: Optional[str] = Field(None, max_length=50)
    graduate_school: Optional[str] = Field(None, max_length=100)
    license_number: Optional[str] = Field(None, max_length=100)
    license_image: Optional[str] = None
    honors: Optional[str] = None
    
    # 坐诊设置
    schedule_desc: Optional[str] = Field(None, max_length=255)
    max_daily_appointments: Optional[int] = Field(None, ge=0)
    online_consult_enabled: Optional[int] = Field(None, ge=0, le=1)
    online_consult_fee: Optional[Decimal] = Field(None, ge=0)
    
    # 展示设置
    page_style: Optional[int] = Field(None, ge=1, le=3)
    promo_video: Optional[str] = None
    tags: Optional[str] = Field(None, max_length=255)
    specialty: Optional[str] = None
    introduction: Optional[str] = None
    
    # 其他设置
    is_recommended: Optional[int] = Field(None, ge=0, le=1)
    sort_order: Optional[int] = Field(None, ge=0)
    status: Optional[int] = Field(None, ge=0, le=1)
    
    # 诊费设置
    use_fee_template: Optional[int] = Field(None, ge=0, le=1)
    
    # 密码更新
    password: Optional[str] = Field(None, min_length=6)

class DoctorResponse(BaseModel):
    """医生响应模型"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    user_id: Optional[str] = None
    store_id: Optional[str] = None
    store_name: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    
    # 基础信息
    name: str
    username: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[int] = 0
    avatar: Optional[str] = None
    banner: Optional[str] = None
    title: Optional[str] = None
    years_of_experience: Optional[int] = 0
    
    # 资质信息
    education: Optional[str] = None
    graduate_school: Optional[str] = None
    license_number: Optional[str] = None
    license_image: Optional[str] = None
    honors: Optional[str] = None
    
    # 坐诊设置
    schedule_desc: Optional[str] = None
    max_daily_appointments: Optional[int] = 0
    online_consult_enabled: Optional[int] = 0
    online_consult_fee: Optional[Decimal] = Decimal("0")
    
    # 展示设置
    page_style: Optional[int] = 1
    promo_video: Optional[str] = None
    tags: Optional[str] = None
    specialty: Optional[str] = None
    introduction: Optional[str] = None
    
    # 其他设置
    is_recommended: Optional[int] = 0
    sort_order: Optional[int] = 0
    status: Optional[int] = 1
    
    # 诊费设置
    use_fee_template: Optional[int] = 0
    
    created_at: datetime
    updated_at: datetime


class DoctorListResponse(BaseModel):
    """医生列表响应模型"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    name: str
    avatar: Optional[str] = None
    banner: Optional[str] = None
    title: Optional[str] = None
    gender: Optional[int] = 0
    store_id: Optional[str] = None
    store_name: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    specialty: Optional[str] = None
    is_recommended: Optional[int] = 0
    tags: Optional[str] = None
    page_style: Optional[int] = 1
    has_available_slots: Optional[bool] = False  # 是否有可预约号源（未来7天内）
    status: Optional[int] = 1  # 状态
