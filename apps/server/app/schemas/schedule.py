from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, time, datetime


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class ScheduleBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    doctor_id: str = Field(..., description="医生ID")
    store_id: Optional[str] = Field(None, description="门店ID")
    schedule_date: date = Field(..., description="排班日期")
    time_slot: Optional[str] = Field(None, pattern="^(AM|PM|morning|afternoon|evening)$", description="时段，可为空（可通过start_time自动计算）")
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    total_slots: int = Field(10, ge=1, le=200, description="总号源")
    appointment_type: str = Field(default="normal", description="预约类型")
    status: int = Field(1, ge=0, le=1)


class ScheduleCreate(ScheduleBase):
    template_id: Optional[str] = Field(None, description="来源模板ID")


class ScheduleBatchCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    doctor_id: str
    start_date: date
    end_date: date
    time_slots: List[str] = Field(..., description="时段列表")
    total_slots: int = Field(10, ge=1)
    weekdays: List[int] = Field(..., description="星期列表 1-7")


class ScheduleUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    total_slots: Optional[int] = Field(None, ge=1, le=200)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    appointment_type: Optional[str] = None
    status: Optional[int] = Field(None, ge=0, le=1)


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    doctor_id: Optional[str] = None
    store_id: Optional[str] = None
    schedule_date: Optional[date] = None
    time_slot: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    total_slots: Optional[int] = 10
    booked_slots: Optional[int] = 0
    appointment_type: Optional[str] = "normal"
    status: Optional[int] = 1
    template_id: Optional[str] = None
    doctor_name: Optional[str] = None
    department_name: Optional[str] = None
    store_name: Optional[str] = None
    created_at: Optional[datetime] = None


class AvailableScheduleResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )

    id: str
    schedule_date: Optional[date] = None
    time_slot: Optional[str] = None
    available_slots: Optional[int] = 0
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    appointment_type: Optional[str] = "normal"

    # 新增字段：规则引擎相关
    total_slots: Optional[int] = None  # 总容量
    booking_open_at: Optional[datetime] = None  # 预约开放时间
    booking_close_at: Optional[datetime] = None  # 预约截止时间
    booking_status: Optional[str] = None  # 预约状态：available/closing_soon/full/closed/not_open
    capacity_percent: Optional[float] = None  # 容量百分比 (0-100)
    urgency_level: Optional[str] = None  # 紧急程度：normal/medium/high
