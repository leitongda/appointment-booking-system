from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.base import BaseSchema


class DoctorScheduleResponse(BaseSchema):
    id: str
    doctor_id: str | None = None
    store_id: str | None = None
    schedule_date: date
    time_slot: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    total_slots: int
    booked_slots: int
    status: int
    is_rest_day: bool | None = False

class DoctorAppointmentResponse(BaseSchema):
    id: str
    appointment_no: str
    patient_id: str | None = None
    patient_name: str
    patient_phone: str | None = None
    schedule_date: date | None = None
    time_slot: str | None = None
    queue_number: int | None = None
    status: int
    sign_in_time: datetime | None = None
    call_time: datetime | None = None
    complete_time: datetime | None = None
    symptom_description: str | None = None
    is_follow_up: bool = False

class QueuePatientResponse(BaseSchema):
    id: str
    appointment_no: str
    queue_number: int | None = None
    patient_name: str
    status: int
    sign_in_time: datetime | None = None
    call_time: datetime | None = None

class PatientHistoryResponse(BaseSchema):
    id: str
    appointment_no: str
    schedule_date: date | None = None
    time_slot: str | None = None
    status: int
    complete_time: datetime | None = None
    symptom_description: str | None = None
    has_medical_record: bool = False

class FollowUpBookingRequest(BaseModel):
    schedule_id: str
