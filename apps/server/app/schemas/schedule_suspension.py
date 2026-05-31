from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date, datetime
from app.core.config import settings
from app.schemas.response import to_camel

class ScheduleSuspensionCreate(BaseModel):
    """创建停诊"""
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    store_id: str = Field(..., description="门店ID")
    doctor_id: str = Field(..., description="医生ID")
    title: str = Field(..., min_length=1, max_length=100, description="停诊标题")
    suspension_date: date = Field(..., description="停诊日期")
    schedule_ids: Optional[List[str]] = Field(None, description="选中的排班ID列表")
    time_slots: Optional[List[str]] = Field(None, description="选中的时段列表,如['08:30-12:00','13:30-17:30']")
    suspension_type: Optional[str] = Field("temporary", description="停诊类型: temporary/full_day/partial/batch/holiday")
    processing_method: Optional[str] = Field(None, description="处置方式: auto_refund/reschedule/change_date/manual")
    reason: Optional[str] = Field(None, max_length=500, description="停诊原因")

class ScheduleSuspensionResponse(BaseModel):
    """停诊响应"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )

    id: str
    store_id: str
    store_name: Optional[str] = None
    doctor_id: str
    doctor_name: Optional[str] = None
    title: str
    suspension_date: date
    schedule_ids: Optional[List[str]] = None
    time_slots: Optional[List[str]] = None
    status: int
    created_at: datetime
    suspension_type: Optional[str] = None
    processing_method: Optional[str] = None
    processing_status: Optional[str] = None
    affected_appointment_count: Optional[int] = None
    reason: Optional[str] = None

class ScheduleSuspensionListParams(BaseModel):
    """查询停诊列表参数"""
    store_id: Optional[str] = None
    doctor_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[int] = Field(None, ge=0, le=1)
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE)

class AvailableScheduleForSuspension(BaseModel):
    """可选排班(用于停诊选择)"""
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )

    schedule_id: str
    time_slot: str  # 如 "08:30-12:00"
    schedule_type: str  # normal/custom
    booked_count: int
    max_patients: int

class SuspensionProcessRequest(BaseModel):
    """停诊处置请求"""
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    processing_method: str = Field(
        ...,
        description="处置方式: auto_refund/reschedule/change_date/manual",
    )

class SuspensionProcessResult(BaseModel):
    """停诊处置结果"""
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )

    suspension_id: str
    processing_method: str
    processing_status: str
    total_affected: int = 0
    success_count: int = 0
    failed_count: int = 0
    details: Optional[List[dict]] = None
