from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime, date, time


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class AppointmentCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    schedule_id: str = Field(..., description="排班ID")
    patient_id: str = Field(..., description="就诊人ID")
    symptom_description: Optional[str] = Field(None, max_length=500, description="病情描述/预填信息")


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    appointment_no: Optional[str] = None
    user_id: Optional[str] = None
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    doctor_id: Optional[str] = None
    doctor_name: Optional[str] = None
    doctor_title: Optional[str] = None
    department_name: Optional[str] = None
    schedule_id: Optional[str] = None
    schedule_date: Optional[date] = None
    time_slot: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    queue_number: Optional[int] = None
    status: Optional[int] = None
    sign_in_time: Optional[datetime] = None
    call_time: Optional[datetime] = None
    complete_time: Optional[datetime] = None
    cancel_time: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    symptom_description: Optional[str] = None
    created_at: Optional[datetime] = None


class AppointmentListQuery(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    status: Optional[int] = None
    patient_id: Optional[str] = None
    doctor_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)


class AppointmentCancelRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    reason: Optional[str] = Field(None, max_length=200)


class AppointmentStatistics(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    total: int = 0
    pending: int = 0
    signed_in: int = 0
    in_progress: int = 0
    completed: int = 0
    cancelled: int = 0
    no_show: int = 0

