from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date

class AppointmentCreate(BaseModel):
    schedule_id: str = Field(..., description="排班ID")
    patient_id: str = Field(..., description="就诊人ID")

class AppointmentResponse(BaseModel):
    id: str
    appointment_no: str
    user_id: str
    patient_id: str
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    doctor_id: str
    doctor_name: Optional[str] = None
    department_name: Optional[str] = None
    schedule_id: str
    schedule_date: Optional[date] = None
    time_slot: Optional[str] = None
    queue_number: Optional[int]
    registration_fee: Optional[float] = None
    status: int
    sign_in_time: Optional[datetime]
    call_time: Optional[datetime]
    complete_time: Optional[datetime]
    cancel_time: Optional[datetime]
    cancel_reason: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class AppointmentListQuery(BaseModel):
    status: Optional[int] = None
    patient_id: Optional[str] = None
    doctor_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)

class AppointmentCancelRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=200)

class AppointmentStatistics(BaseModel):
    total: int = 0
    pending: int = 0
    signed_in: int = 0
    in_progress: int = 0
    completed: int = 0
    cancelled: int = 0
    no_show: int = 0

