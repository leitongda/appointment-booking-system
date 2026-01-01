from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import time, datetime, date
from enum import Enum


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class AppointmentType(str, Enum):
    """预约类型"""
    URGENT = "urgent"  # 加急
    NORMAL = "normal"  # 普通
    EXPERT = "expert"  # 专家
    MEDICAL_INSURANCE = "medical_insurance"  # 医保
    SELF_PAY = "self_pay"  # 自费


class ScheduleMode(str, Enum):
    """排班方式"""
    WEEKLY = "weekly"  # 每周循环
    MONTH_WEEK_1 = "month_week_1"  # 每月第一周
    MONTH_WEEK_2 = "month_week_2"  # 每月第二周
    MONTH_WEEK_3 = "month_week_3"  # 每月第三周
    MONTH_WEEK_4 = "month_week_4"  # 每月第四周
    MONTH_WEEK_5 = "month_week_5"  # 每月第五周
    YEAR_ODD_WEEK = "year_odd_week"  # 本年奇数周
    YEAR_EVEN_WEEK = "year_even_week"  # 本年偶数周


class BreakTime(BaseModel):
    """排除时间段（如午休时间）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    start_time: time = Field(..., description="开始时间")
    end_time: time = Field(..., description="结束时间")


class ScheduleTemplateBase(BaseModel):
    """排班模板基础模型"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    name: str = Field(..., max_length=100, description="模板名称")
    store_id: str = Field(..., description="门店ID")
    doctor_id: str = Field(..., description="医生ID")
    department_id: str = Field(..., description="科室ID")
    weekdays: List[int] = Field(..., description="星期数组 1-7，如[1,2,3,4,5]")
    appointment_type: AppointmentType = Field(default=AppointmentType.NORMAL, description="预约类型")
    start_time: time = Field(..., description="开始时间")
    end_time: time = Field(..., description="结束时间")
    slot_count: int = Field(default=1, ge=1, le=50, description="班次数量")
    slot_capacity: int = Field(default=10, ge=1, le=200, description="每班次人数")
    schedule_mode: ScheduleMode = Field(default=ScheduleMode.WEEKLY, description="排班方式")
    break_times: Optional[List[BreakTime]] = Field(None, description="排除时间段列表（如午休时间）")


class ScheduleTemplateCreate(ScheduleTemplateBase):
    """创建排班模板"""
    pass


class ScheduleTemplateUpdate(BaseModel):
    """更新排班模板"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    name: Optional[str] = Field(None, max_length=100, description="模板名称")
    store_id: Optional[str] = None
    doctor_id: Optional[str] = None
    department_id: Optional[str] = None
    weekdays: Optional[List[int]] = Field(None, description="星期数组 1-7")
    appointment_type: Optional[AppointmentType] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    slot_count: Optional[int] = Field(None, ge=1, le=50)
    slot_capacity: Optional[int] = Field(None, ge=1, le=200)
    schedule_mode: Optional[ScheduleMode] = None
    break_times: Optional[List[BreakTime]] = Field(None, description="排除时间段列表（如午休时间）")
    status: Optional[int] = Field(None, ge=0, le=1)


class ScheduleTemplateResponse(BaseModel):
    """排班模板响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    name: Optional[str] = None
    store_id: Optional[str] = None
    doctor_id: Optional[str] = None
    department_id: Optional[str] = None
    weekdays: Optional[List[int]] = None
    appointment_type: Optional[str] = "normal"
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    slot_count: Optional[int] = 1
    slot_capacity: Optional[int] = 10
    schedule_mode: Optional[str] = "weekly"
    break_times: Optional[List[BreakTime]] = None
    status: Optional[int] = 1
    store_name: Optional[str] = None
    doctor_name: Optional[str] = None
    department_name: Optional[str] = None
    last_generated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ScheduleGenerateRequest(BaseModel):
    """根据模板生成排班请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    template_ids: List[str] = Field(..., description="模板ID列表")
    start_date: Optional[date] = Field(None, description="开始日期，为空则默认今天")
    end_date: Optional[date] = Field(None, description="结束日期，为空则默认1年后")


class ScheduleBatchAddRequest(BaseModel):
    """批量添加排班请求（不依赖模板）"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    store_id: str = Field(..., description="门店ID")
    doctor_id: str = Field(..., description="医生ID")
    department_id: str = Field(..., description="科室ID")
    appointment_type: AppointmentType = Field(default=AppointmentType.NORMAL, description="预约类型")
    start_time: time = Field(..., description="开始时间")
    end_time: time = Field(..., description="结束时间")
    slot_count: int = Field(default=1, ge=1, le=50, description="班次数量")
    slot_capacity: int = Field(default=10, ge=1, le=200, description="每班次人数")
    schedule_mode: ScheduleMode = Field(default=ScheduleMode.WEEKLY, description="排班方式")
    break_times: Optional[List[BreakTime]] = Field(None, description="排除时间段列表（如午休时间）")
    weekdays: List[int] = Field(..., description="星期列表 1-7")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")


class ScheduleSlotPreview(BaseModel):
    """班次预览项"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    schedule_date: date = Field(..., description="排班日期")
    start_time: time = Field(..., description="开始时间")
    end_time: time = Field(..., description="结束时间")
    time_slot: str = Field(..., description="时段: morning/afternoon/evening")
    slot_capacity: int = Field(..., description="可预约人数")
    weekday: int = Field(..., description="星期几 1-7")
    weekday_name: str = Field(..., description="星期名称")


class SchedulePreviewGenerateRequest(BaseModel):
    """预览生成排班请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    template_ids: List[str] = Field(..., description="模板ID列表")
    start_date: Optional[date] = Field(None, description="开始日期，为空则默认今天")
    end_date: Optional[date] = Field(None, description="结束日期，为空则默认30天后")


class SchedulePreviewGenerateResponse(BaseModel):
    """预览生成排班响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    slots: List[ScheduleSlotPreview] = Field(..., description="预览班次列表")
    total_count: int = Field(..., description="总班次数")
    template_id: str = Field(..., description="模板ID")
    template_name: str = Field(..., description="模板名称")
    doctor_name: Optional[str] = None
    department_name: Optional[str] = None


class SlotCapacityOverride(BaseModel):
    """班次容量覆盖"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    schedule_date: date = Field(..., description="排班日期")
    start_time: time = Field(..., description="开始时间")
    end_time: time = Field(..., description="结束时间")
    slot_capacity: int = Field(..., ge=1, le=200, description="可预约人数")


class ScheduleGenerateWithCapacityRequest(BaseModel):
    """带自定义容量的生成排班请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    template_ids: List[str] = Field(..., description="模板ID列表")
    start_date: Optional[date] = Field(None, description="开始日期，为空则默认今天")
    end_date: Optional[date] = Field(None, description="结束日期，为空则默认1年后")
    slot_capacities: Optional[List[SlotCapacityOverride]] = Field(None, description="自定义班次容量列表")
