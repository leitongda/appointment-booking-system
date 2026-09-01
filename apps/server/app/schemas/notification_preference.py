from datetime import datetime

from pydantic import Field

from app.schemas.base import BaseRequestSchema, BaseSchema


class NotificationPreferenceResponse(BaseSchema):

    id: str
    tenant_id: str | None = None
    user_id: str
    user_type: str
    appointment_enabled: bool = True
    reminder_enabled: bool = True
    queue_call_enabled: bool = True
    stop_clinic_enabled: bool = True
    system_enabled: bool = True
    sms_enabled: bool = True
    email_enabled: bool = True
    wechat_enabled: bool = True
    in_app_enabled: bool = True
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class NotificationPreferenceUpdate(BaseRequestSchema):

    appointment_enabled: bool | None = None
    reminder_enabled: bool | None = None
    queue_call_enabled: bool | None = None
    stop_clinic_enabled: bool | None = None
    system_enabled: bool | None = None
    sms_enabled: bool | None = None
    email_enabled: bool | None = None
    wechat_enabled: bool | None = None
    in_app_enabled: bool | None = None
    quiet_hours_start: str | None = Field(None, max_length=5)
    quiet_hours_end: str | None = Field(None, max_length=5)
