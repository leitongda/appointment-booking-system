from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import date, datetime
from enum import Enum
from app.core.config import settings


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


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
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    doctor_id: str = Field(..., description="医生ID")
    schedule_id: Optional[str] = Field(None, description="排班ID")
    stop_date: date = Field(..., description="停诊日期")
    stop_period: Period = Field(..., description="停诊时段")
    reason: str = Field(..., min_length=1, max_length=500, description="申请原因")


# 调班申请
class ScheduleChangeCreate(BaseModel):
    """创建调班申请"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    doctor_id: str = Field(..., description="医生ID")
    original_date: date = Field(..., description="原日期")
    original_period: Period = Field(..., description="原时段")
    target_date: date = Field(..., description="目标日期")
    target_period: Period = Field(..., description="目标时段")
    reason: str = Field(..., min_length=1, max_length=500, description="申请原因")


# 审核
class ReviewRequest(BaseModel):
    """审核申请"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    status: RequestStatus = Field(..., description="审核结果")
    review_comment: Optional[str] = Field(None, max_length=500, description="审核意见")


# 响应
class LeaveRequestResponse(BaseModel):
    """申请响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    doctor_id: Optional[str] = None
    doctor_name: Optional[str] = None
    request_type: Optional[str] = None
    schedule_id: Optional[str] = None
    stop_date: Optional[date] = None
    stop_period: Optional[str] = None
    original_date: Optional[date] = None
    original_period: Optional[str] = None
    target_date: Optional[date] = None
    target_period: Optional[str] = None
    reason: Optional[str] = None
    status: Optional[str] = None
    reviewer_id: Optional[str] = None
    review_comment: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    affected_appointments: Optional[int] = 0
    created_at: Optional[datetime] = None


class LeaveRequestQuery(BaseModel):
    """查询参数"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    doctor_id: Optional[str] = None
    request_type: Optional[RequestType] = None
    status: Optional[RequestStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    store_id: Optional[str] = None  # 门店过滤
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE)
