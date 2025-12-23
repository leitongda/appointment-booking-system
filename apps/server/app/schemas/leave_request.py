from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from enum import Enum


class RequestType(str, Enum):
    STOP_CLINIC = "stop_clinic"
    SCHEDULE_CHANGE = "schedule_change"


class RequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class Period(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    ALL = "all"


# 停诊申请
class StopClinicCreate(BaseModel):
    """创建停诊申请"""
    doctor_id: str = Field(..., description="医生ID")
    schedule_id: Optional[str] = Field(None, description="排班ID")
    stop_date: date = Field(..., description="停诊日期")
    stop_period: Period = Field(..., description="停诊时段")
    reason: str = Field(..., min_length=1, max_length=500, description="申请原因")


# 调班申请
class ScheduleChangeCreate(BaseModel):
    """创建调班申请"""
    doctor_id: str = Field(..., description="医生ID")
    original_date: date = Field(..., description="原日期")
    original_period: Period = Field(..., description="原时段")
    target_date: date = Field(..., description="目标日期")
    target_period: Period = Field(..., description="目标时段")
    reason: str = Field(..., min_length=1, max_length=500, description="申请原因")


# 审核
class ReviewRequest(BaseModel):
    """审核申请"""
    status: RequestStatus = Field(..., description="审核结果")
    review_comment: Optional[str] = Field(None, max_length=500, description="审核意见")


# 响应
class LeaveRequestResponse(BaseModel):
    """申请响应"""
    id: str
    doctor_id: str
    doctor_name: Optional[str] = None
    request_type: str
    schedule_id: Optional[str]
    stop_date: Optional[date]
    stop_period: Optional[str]
    original_date: Optional[date]
    original_period: Optional[str]
    target_date: Optional[date]
    target_period: Optional[str]
    reason: str
    status: str
    reviewer_id: Optional[str]
    review_comment: Optional[str]
    reviewed_at: Optional[datetime]
    affected_appointments: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class LeaveRequestQuery(BaseModel):
    """查询参数"""
    doctor_id: Optional[str] = None
    request_type: Optional[RequestType] = None
    status: Optional[RequestStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    store_id: Optional[str] = None  # 门店过滤
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
