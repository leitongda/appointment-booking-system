from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.base import BaseRequestSchema, BaseSchema


class DoctorBase(BaseRequestSchema):

    # 基础信息
    store_id: str | None = Field(None, description="所属门店ID")
    department_id: str = Field(..., description="科室ID")
    name: str = Field(..., max_length=50, description="医生姓名")
    username: str | None = Field(None, max_length=50, description="医生登录账号")
    phone: str | None = Field(None, max_length=20, description="手机号")
    gender: int = Field(0, ge=0, le=2, description="性别 0未知 1男 2女")
    avatar: str | None = Field(None, description="头像URL")
    banner: str | None = Field(None, description="医生banner图URL")
    title: str | None = Field(None, max_length=50, description="职称")
    years_of_experience: int = Field(0, ge=0, description="医龄(年)")
    
    # 资质信息
    education: str | None = Field(None, max_length=50, description="学历")
    graduate_school: str | None = Field(None, max_length=100, description="毕业院校")
    license_number: str | None = Field(None, max_length=100, description="执业证书编号")
    license_image: str | None = Field(None, description="执业证书图片URL")
    honors: str | None = Field(None, description="所获荣誉")
    
    # 坐诊设置
    schedule_desc: str | None = Field(None, max_length=255, description="坐诊时间说明")
    max_daily_appointments: int = Field(0, ge=0, description="每日最大接诊量,0表示不限制")
    online_consult_enabled: int = Field(0, ge=0, le=1, description="是否支持在线问诊 0否 1是")
    online_consult_fee: Decimal = Field(Decimal("0"), ge=0, description="在线问诊费用")
    
    # 展示设置
    page_style: int = Field(1, ge=1, le=3, description="页面风格 1/2/3")
    promo_video: str | None = Field(None, description="宣传视频URL")
    tags: str | None = Field(None, max_length=255, description="标签,逗号分隔")
    specialty: str | None = Field(None, description="擅长")
    introduction: str | None = Field(None, description="简介")
    
    # 其他设置
    is_recommended: int = Field(0, ge=0, le=1, description="是否推荐")
    sort_order: int = Field(0, ge=0, description="排序")
    status: int = Field(1, ge=0, le=1, description="状态")
    
    # 诊费设置
    use_fee_template: int = Field(0, ge=0, le=1, description="是否使用诊费模板 0否 1是")

class DoctorCreate(DoctorBase):
    password: str | None = Field(None, min_length=6, description="医生账号密码")

class DoctorUpdate(BaseRequestSchema):

    # 基础信息
    store_id: str | None = None
    department_id: str | None = None
    name: str | None = Field(None, max_length=50)
    username: str | None = Field(None, max_length=50)
    phone: str | None = Field(None, max_length=20)
    gender: int | None = Field(None, ge=0, le=2)
    avatar: str | None = None
    banner: str | None = None
    title: str | None = Field(None, max_length=50)
    years_of_experience: int | None = Field(None, ge=0)
    
    # 资质信息
    education: str | None = Field(None, max_length=50)
    graduate_school: str | None = Field(None, max_length=100)
    license_number: str | None = Field(None, max_length=100)
    license_image: str | None = None
    honors: str | None = None
    
    # 坐诊设置
    schedule_desc: str | None = Field(None, max_length=255)
    max_daily_appointments: int | None = Field(None, ge=0)
    online_consult_enabled: int | None = Field(None, ge=0, le=1)
    online_consult_fee: Decimal | None = Field(None, ge=0)
    
    # 展示设置
    page_style: int | None = Field(None, ge=1, le=3)
    promo_video: str | None = None
    tags: str | None = Field(None, max_length=255)
    specialty: str | None = None
    introduction: str | None = None
    
    # 其他设置
    is_recommended: int | None = Field(None, ge=0, le=1)
    sort_order: int | None = Field(None, ge=0)
    status: int | None = Field(None, ge=0, le=1)
    
    # 诊费设置
    use_fee_template: int | None = Field(None, ge=0, le=1)
    
    # 密码更新
    password: str | None = Field(None, min_length=6)

class DoctorResponse(BaseSchema):
    """医生响应模型"""

    id: str
    user_id: str | None = None
    store_id: str | None = None
    store_name: str | None = None
    department_id: str | None = None
    department_name: str | None = None
    
    # 基础信息
    name: str
    username: str | None = None
    phone: str | None = None
    email: str | None = None
    gender: int | None = 0
    avatar: str | None = None
    banner: str | None = None
    title: str | None = None
    years_of_experience: int | None = 0
    
    # 资质信息
    education: str | None = None
    graduate_school: str | None = None
    license_number: str | None = None
    license_image: str | None = None
    honors: str | None = None
    
    # 坐诊设置
    schedule_desc: str | None = None
    max_daily_appointments: int | None = 0
    online_consult_enabled: int | None = 0
    online_consult_fee: Decimal | None = Decimal("0")
    
    # 展示设置
    page_style: int | None = 1
    promo_video: str | None = None
    tags: str | None = None
    specialty: str | None = None
    introduction: str | None = None
    
    # 其他设置
    is_recommended: int | None = 0
    sort_order: int | None = 0
    status: int | None = 1
    
    # 诊费设置
    use_fee_template: int | None = 0
    
    created_at: datetime
    updated_at: datetime

class DoctorListResponse(BaseSchema):
    """医生列表响应模型"""

    id: str
    name: str
    avatar: str | None = None
    banner: str | None = None
    title: str | None = None
    gender: int | None = 0
    store_id: str | None = None
    store_name: str | None = None
    department_id: str | None = None
    department_name: str | None = None
    specialty: str | None = None
    is_recommended: int | None = 0
    tags: str | None = None
    page_style: int | None = 1
    has_available_slots: bool | None = False  # 是否有可预约号源（未来7天内）
    status: int | None = 1  # 状态
