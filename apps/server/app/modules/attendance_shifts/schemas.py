from datetime import datetime

from pydantic import Field

from app.schemas.base import BaseSchema


class AttendanceShiftCreate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    start_time: str = Field(..., description="HH:MM")
    end_time: str = Field(..., description="HH:MM")
    break_start: str | None = None
    break_end: str | None = None
    grace_minutes: int = 0
    late_threshold_minutes: int = 0
    early_threshold_minutes: int = 0
    is_flexible: bool = False
    enabled: bool = True


class AttendanceShiftUpdate(BaseSchema):
    name: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    break_start: str | None = None
    break_end: str | None = None
    grace_minutes: int | None = None
    late_threshold_minutes: int | None = None
    early_threshold_minutes: int | None = None
    is_flexible: bool | None = None
    enabled: bool | None = None


class AttendanceShiftResponse(BaseSchema):
    id: str
    name: str
    code: str
    start_time: str
    end_time: str
    break_start: str | None = None
    break_end: str | None = None
    grace_minutes: int
    late_threshold_minutes: int
    early_threshold_minutes: int
    is_flexible: bool
    enabled: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
