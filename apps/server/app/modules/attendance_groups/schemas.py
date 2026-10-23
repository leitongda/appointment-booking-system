"""签到组管理 Schema 定义"""

from datetime import datetime

from pydantic import Field

from app.schemas.base import BaseSchema


class AttendanceGroupCreate(BaseSchema):
    """创建签到组"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    check_method: str = "gps"  # gps/wifi/device
    location_lat: float | None = None
    location_lng: float | None = None
    location_radius: int = 300
    wifi_ssid: str | None = None
    wifi_ssids: str | None = None
    device_whitelist: str | None = None
    require_device_bind: bool = False
    enabled: bool = True


class AttendanceGroupUpdate(BaseSchema):
    """更新签到组"""
    name: str | None = None
    description: str | None = None
    check_method: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    location_radius: int | None = None
    wifi_ssid: str | None = None
    wifi_ssids: str | None = None
    device_whitelist: str | None = None
    require_device_bind: bool | None = None
    enabled: bool | None = None


class AttendanceGroupResponse(BaseSchema):
    """签到组响应"""
    id: str
    name: str
    description: str | None = None
    check_method: str
    location_lat: float | None = None
    location_lng: float | None = None
    location_radius: int
    wifi_ssid: str | None = None
    wifi_ssids: str | None = None
    device_whitelist: str | None = None
    require_device_bind: bool = False
    enabled: bool
    member_count: int = 0
    created_at: datetime | None = None


class GroupMemberAdd(BaseSchema):
    """批量添加成员"""
    account_ids: list[str] = Field(..., min_length=1)


class GroupMemberResponse(BaseSchema):
    """成员响应"""
    id: str
    account_id: str
    account_name: str | None = None
    created_at: str | None = None
