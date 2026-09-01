from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.schemas.base import BaseRequestSchema
from app.schemas.response import to_camel


class DoctorBookingSettingBase(BaseRequestSchema):
    """医生预约设置基础模型"""

    store_id: str = Field(..., description="门店ID")
    doctor_id: str = Field(..., description="医生ID")
    booking_start_offset: int = Field(0, ge=0, le=30, description="预约开始偏移天数，0表示当天，n表示n+1天后开始")
    booking_range_days: int = Field(14, ge=1, le=90, description="预约范围天数，1-90天")
    release_time: str = Field("00:00", max_length=5, description="放号时间 HH:mm格式")
    status: int = Field(1, ge=0, le=1, description="状态: 0禁用 1启用")

class DoctorBookingSettingCreate(DoctorBookingSettingBase):
    """创建医生预约设置"""
    pass

class DoctorBookingSettingUpdate(BaseRequestSchema):
    """更新医生预约设置"""

    booking_start_offset: int | None = Field(None, ge=0, le=30, description="预约开始偏移天数")
    booking_range_days: int | None = Field(None, ge=1, le=90, description="预约范围天数")
    release_time: str | None = Field(None, max_length=5, description="放号时间")
    status: int | None = Field(None, ge=0, le=1, description="状态")

class DoctorBookingSettingResponse(DoctorBookingSettingBase):
    """医生预约设置响应"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )
    
    id: str
    store_name: str | None = Field(None, description="门店名称")
    doctor_name: str | None = Field(None, description="医生名称")
    created_at: datetime
    updated_at: datetime

class DoctorBookingSettingQuery(BaseRequestSchema):
    """医生预约设置查询参数"""

    store_id: str | None = Field(None, description="门店ID筛选")
    doctor_id: str | None = Field(None, description="医生ID筛选")
    status: int | None = Field(None, description="状态筛选")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量")
