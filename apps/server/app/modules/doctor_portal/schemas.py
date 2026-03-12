from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class DoctorScheduleResponse(BaseModel):
    id: str
    schedule_date: date
    time_slot: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_slots: int
    booked_slots: int
    status: int
    is_rest_day: Optional[bool] = False

    class Config:
        from_attributes = True


class DoctorAppointmentResponse(BaseModel):
    id: str
    appointment_no: str
    patient_id: Optional[str] = None
    patient_name: str
    patient_phone: Optional[str] = None
    schedule_date: Optional[date] = None
    time_slot: Optional[str] = None
    queue_number: Optional[int] = None
    status: int
    sign_in_time: Optional[datetime] = None
    call_time: Optional[datetime] = None
    complete_time: Optional[datetime] = None
    symptom_description: Optional[str] = None
    is_follow_up: bool = False

    class Config:
        from_attributes = True


class QueuePatientResponse(BaseModel):
    id: str
    appointment_no: str
    queue_number: Optional[int] = None
    patient_name: str
    status: int
    sign_in_time: Optional[datetime] = None
    call_time: Optional[datetime] = None


class PatientHistoryResponse(BaseModel):
    id: str
    appointment_no: str
    schedule_date: Optional[date] = None
    time_slot: Optional[str] = None
    status: int
    complete_time: Optional[datetime] = None
    symptom_description: Optional[str] = None
    has_medical_record: bool = False

    class Config:
        from_attributes = True


class FollowUpBookingRequest(BaseModel):
    schedule_id: str
