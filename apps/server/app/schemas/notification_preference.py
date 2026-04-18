from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


def to_camel(string: str) -> str:
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class NotificationPreferenceResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )

    id: str
    tenant_id: Optional[str] = None
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
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class NotificationPreferenceUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    appointment_enabled: Optional[bool] = None
    reminder_enabled: Optional[bool] = None
    queue_call_enabled: Optional[bool] = None
    stop_clinic_enabled: Optional[bool] = None
    system_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    wechat_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = Field(None, max_length=5)
    quiet_hours_end: Optional[str] = Field(None, max_length=5)
