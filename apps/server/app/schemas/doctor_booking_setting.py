from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.core.config import settings
from app.schemas.response import to_camel

class DoctorBookingSettingBase(BaseModel):
    """医生预约设置基础模型"""
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )
    
    store_id: str = Field(..., description="门店ID")
    doctor_id: str = Field(..., description="医生ID")
    booking_start_offset: int = Field(0, ge=0, le=30, description="预约开始偏移天数，0表示当天，n表示n+1天后开始")
    booking_range_days: int = Field(14, ge=1, le=90, description="预约范围天数，1-90天")
    release_time: str = Field("00:00", max_length=5, description="放号时间 HH:mm格式")
    status: int = Field(1, ge=0, le=1, description="状态: 0禁用 1启用")

class DoctorBookingSettingCreate(DoctorBookingSettingBase):
    """创建医生预约设置"""
    pass

class DoctorBookingSettingUpdate(BaseModel):
    """更新医生预约设置"""
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )
    
    booking_start_offset: Optional[int] = Field(None, ge=0, le=30, description="预约开始偏移天数")
    booking_range_days: Optional[int] = Field(None, ge=1, le=90, description="预约范围天数")
    release_time: Optional[str] = Field(None, max_length=5, description="放号时间")
    status: Optional[int] = Field(None, ge=0, le=1, description="状态")

class DoctorBookingSettingResponse(DoctorBookingSettingBase):
    """医生预约设置响应"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )
    
    id: str
    store_name: Optional[str] = Field(None, description="门店名称")
    doctor_name: Optional[str] = Field(None, description="医生名称")
    created_at: datetime
    updated_at: datetime

class DoctorBookingSettingQuery(BaseModel):
    """医生预约设置查询参数"""
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )
    
    store_id: Optional[str] = Field(None, description="门店ID筛选")
    doctor_id: Optional[str] = Field(None, description="医生ID筛选")
    status: Optional[int] = Field(None, description="状态筛选")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量")
