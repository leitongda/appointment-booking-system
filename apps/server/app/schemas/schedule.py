from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, time, datetime

class ScheduleBase(BaseModel):
    doctor_id: str = Field(..., description="医生ID")
    store_id: Optional[str] = Field(None, description="门店ID")
    schedule_date: date = Field(..., description="排班日期")
    time_slot: str = Field(..., pattern="^(AM|PM|morning|afternoon|evening)$", description="时段")
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    total_slots: int = Field(10, ge=1, le=200, description="总号源")
    appointment_type: str = Field(default="normal", description="预约类型")
    status: int = Field(1, ge=0, le=1)

class ScheduleCreate(ScheduleBase):
    template_id: Optional[str] = Field(None, description="来源模板ID")

class ScheduleBatchCreate(BaseModel):
    doctor_id: str
    start_date: date
    end_date: date
    time_slots: List[str] = Field(..., description="时段列表")
    total_slots: int = Field(10, ge=1)
    weekdays: List[int] = Field(..., description="星期列表 1-7")

class ScheduleUpdate(BaseModel):
    total_slots: Optional[int] = Field(None, ge=1, le=200)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    appointment_type: Optional[str] = None
    status: Optional[int] = Field(None, ge=0, le=1)

class ScheduleResponse(ScheduleBase):
    id: str
    booked_slots: int
    template_id: Optional[str] = None
    doctor_name: Optional[str] = None
    department_name: Optional[str] = None
    store_name: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class AvailableScheduleResponse(BaseModel):
    id: str
    schedule_date: date
    time_slot: str
    available_slots: int
    start_time: Optional[time]
    end_time: Optional[time]
    appointment_type: Optional[str] = "normal"
