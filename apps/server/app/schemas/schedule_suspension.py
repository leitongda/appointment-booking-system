from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.schemas.base import BaseRequestSchema, BaseSchema
from app.schemas.response import to_camel


class ScheduleSuspensionCreate(BaseRequestSchema):
    """创建停诊"""

    store_id: str = Field(..., description="门店ID")
    doctor_id: str = Field(..., description="医生ID")
    title: str = Field(..., min_length=1, max_length=100, description="停诊标题")
    suspension_date: date = Field(..., description="停诊日期")
    schedule_ids: list[str] | None = Field(None, description="选中的排班ID列表")
    time_slots: list[str] | None = Field(None, description="选中的时段列表,如['08:30-12:00','13:30-17:30']")
    suspension_type: str | None = Field("temporary", description="停诊类型: temporary/full_day/partial/batch/holiday")
    processing_method: str | None = Field(None, description="处置方式: auto_refund/reschedule/change_date/manual")
    reason: str | None = Field(None, max_length=500, description="停诊原因")

class ScheduleSuspensionResponse(BaseSchema):
    """停诊响应"""

    id: str
    store_id: str
    store_name: str | None = None
    doctor_id: str
    doctor_name: str | None = None
    title: str
    suspension_date: date
    schedule_ids: list[str] | None = None
    time_slots: list[str] | None = None
    status: int
    created_at: datetime
    suspension_type: str | None = None
    processing_method: str | None = None
    processing_status: str | None = None
    affected_appointment_count: int | None = None
    reason: str | None = None

class ScheduleSuspensionListParams(BaseModel):
    """查询停诊列表参数"""
    store_id: str | None = None
    doctor_id: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: int | None = Field(None, ge=0, le=1)
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

class SuspensionProcessRequest(BaseRequestSchema):
    """停诊处置请求"""

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
    details: list[dict] | None = None
