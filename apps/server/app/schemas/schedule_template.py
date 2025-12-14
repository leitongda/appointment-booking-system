from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import time, datetime, date
from enum import Enum


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


class ScheduleTemplateBase(BaseModel):
    """排班模板基础模型"""
    name: str = Field(..., max_length=100, description="模板名称")
    store_id: str = Field(..., description="门店ID")
    doctor_id: str = Field(..., description="医生ID")
    department_id: str = Field(..., description="科室ID")
    weekday: int = Field(..., ge=1, le=7, description="星期 1-7")
    appointment_type: AppointmentType = Field(default=AppointmentType.NORMAL, description="预约类型")
    start_time: time = Field(..., description="开始时间")
    end_time: time = Field(..., description="结束时间")
    total_slots: int = Field(default=10, ge=1, le=200, description="班次人数")
    schedule_mode: ScheduleMode = Field(default=ScheduleMode.WEEKLY, description="排班方式")


class ScheduleTemplateCreate(ScheduleTemplateBase):
    """创建排班模板"""
    pass


class ScheduleTemplateUpdate(BaseModel):
    """更新排班模板"""
    name: Optional[str] = Field(None, max_length=100, description="模板名称")
    store_id: Optional[str] = None
    doctor_id: Optional[str] = None
    department_id: Optional[str] = None
    weekday: Optional[int] = Field(None, ge=1, le=7)
    appointment_type: Optional[AppointmentType] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    total_slots: Optional[int] = Field(None, ge=1, le=200)
    schedule_mode: Optional[ScheduleMode] = None
    status: Optional[int] = Field(None, ge=0, le=1)


class ScheduleTemplateResponse(ScheduleTemplateBase):
    """排班模板响应"""
    id: str
    status: int
    store_name: Optional[str] = None
    doctor_name: Optional[str] = None
    department_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScheduleGenerateRequest(BaseModel):
    """根据模板生成排班请求"""
    template_ids: List[str] = Field(..., description="模板ID列表")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")


class ScheduleBatchAddRequest(BaseModel):
    """批量添加排班请求（不依赖模板）"""
    store_id: str = Field(..., description="门店ID")
    doctor_id: str = Field(..., description="医生ID")
    department_id: str = Field(..., description="科室ID")
    appointment_type: AppointmentType = Field(default=AppointmentType.NORMAL, description="预约类型")
    start_time: time = Field(..., description="开始时间")
    end_time: time = Field(..., description="结束时间")
    total_slots: int = Field(default=10, ge=1, le=200, description="班次人数")
    schedule_mode: ScheduleMode = Field(default=ScheduleMode.WEEKLY, description="排班方式")
    weekdays: List[int] = Field(..., description="星期列表 1-7")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
