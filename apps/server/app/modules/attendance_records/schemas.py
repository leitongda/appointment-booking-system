"""考勤打卡记录 Schema 定义"""

from pydantic import Field

from app.schemas.base import BaseSchema


class CheckInRequest(BaseSchema):
    """签到请求"""
    lat: float = Field(..., description="纬度")
    lng: float = Field(..., description="经度")
    device_info: str | None = None
    group_id: str | None = None
    wifi_ssid: str | None = None
    device_id: str | None = None
    remark: str | None = None


class CheckOutRequest(BaseSchema):
    """签退请求"""
    lat: float = Field(..., description="纬度")
    lng: float = Field(..., description="经度")
    device_info: str | None = None
    remark: str | None = None


class AttendanceRecordResponse(BaseSchema):
    """考勤记录响应"""
    id: str
    account_id: str
    account_name: str | None = None
    shift_id: str | None = None
    shift_name: str | None = None
    group_id: str | None = None
    check_date: str
    check_in_time: str | None = None
    check_out_time: str | None = None
    status: str
    late_minutes: int
    early_minutes: int
    work_hours: float | None = None
    remark: str | None = None


class DailyStatResponse(BaseSchema):
    """每日考勤统计响应"""
    date: str
    total: int
    normal: int
    late: int
    early: int
    absent: int
    leave: int
