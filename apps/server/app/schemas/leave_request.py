from datetime import date, datetime

from pydantic import Field

from app.core.config import settings
from app.enums.schedule import Period, RequestStatus, RequestType  # noqa: F401 — re-export
from app.schemas.base import BaseRequestSchema, BaseSchema


# 停诊申请
class StopClinicCreate(BaseRequestSchema):
    """创建停诊申请"""

    doctor_id: str = Field(..., description="医生ID")
    schedule_id: str | None = Field(None, description="排班ID")
    stop_date: date = Field(..., description="停诊日期")
    stop_period: Period = Field(..., description="停诊时段")
    reason: str = Field(..., min_length=1, max_length=500, description="申请原因")

# 调班申请
class ScheduleChangeCreate(BaseRequestSchema):
    """创建调班申请"""

    doctor_id: str = Field(..., description="医生ID")
    original_date: date = Field(..., description="原日期")
    original_period: Period = Field(..., description="原时段")
    target_date: date = Field(..., description="目标日期")
    target_period: Period = Field(..., description="目标时段")
    reason: str = Field(..., min_length=1, max_length=500, description="申请原因")

# 审核
class ReviewRequest(BaseRequestSchema):
    """审核申请"""

    status: RequestStatus = Field(..., description="审核结果")
    review_comment: str | None = Field(None, max_length=500, description="审核意见")

# 响应
class LeaveRequestResponse(BaseSchema):
    """申请响应"""

    id: str
    doctor_id: str | None = None
    doctor_name: str | None = None
    request_type: str | None = None
    schedule_id: str | None = None
    stop_date: date | None = None
    stop_period: str | None = None
    original_date: date | None = None
    original_period: str | None = None
    target_date: date | None = None
    target_period: str | None = None
    reason: str | None = None
    status: str | None = None
    reviewer_id: str | None = None
    review_comment: str | None = None
    reviewed_at: datetime | None = None
    affected_appointments: int | None = 0
    created_at: datetime | None = None

class LeaveRequestQuery(BaseRequestSchema):
    """查询参数"""

    doctor_id: str | None = None
    request_type: RequestType | None = None
    status: RequestStatus | None = None
    start_date: date | None = None
    end_date: date | None = None
    store_id: str | None = None  # 门店过滤
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE)
