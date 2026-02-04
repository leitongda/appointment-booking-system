from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date, time, datetime
from app.schemas.schedule_template import AppointmentType
from app.core.config import settings


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class TimePeriod(BaseModel):
    """时间段配置"""
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )
    
    start_time: time = Field(..., description="开始时间")
    end_time: time = Field(..., description="结束时间")
    appointment_type: AppointmentType = Field(..., description="预约类型")
    slot_count: Optional[int] = Field(None, ge=1, le=50, description="排班数量(均分数量),不填则不均分")
    max_patients: int = Field(1, ge=1, le=100, description="预约人数(每个班次)")


class CustomScheduleCreate(BaseModel):
    """创建自定义排班"""
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )
    
    store_id: str = Field(..., description="门店ID")
    department_id: str = Field(..., description="科室ID")
    doctor_id: str = Field(..., description="医生ID")
    schedule_dates: List[date] = Field(..., min_length=1, description="排班日期列表(支持多选)")
    time_periods: List[TimePeriod] = Field(..., min_length=1, description="排班时段配置列表")


class CustomScheduleResponse(BaseModel):
    """自定义排班响应"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )
    
    id: str
    store_id: str
    store_name: Optional[str] = None
    department_id: str
    department_name: Optional[str] = None
    doctor_id: str
    doctor_name: Optional[str] = None
    schedule_date: date
    start_time: time
    end_time: time
    appointment_type: str
    max_patients: int
    booked_count: int
    status: int
    created_at: datetime
    is_rest_day: Optional[bool] = False  # 是否在休息日（后端计算）


class CustomScheduleListParams(BaseModel):
    """查询自定义排班列表参数"""
    store_id: Optional[str] = None
    department_id: Optional[str] = None
    doctor_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    appointment_type: Optional[AppointmentType] = None
    status: Optional[int] = Field(None, ge=0, le=1)
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE)


class EffectiveScheduleParams(BaseModel):
    """查询生效班次参数"""
    store_id: Optional[str] = None
    doctor_id: Optional[str] = None
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
