from datetime import datetime

from pydantic import Field

from app.schemas.base import BaseSchema


class DoctorReviewCreate(BaseSchema):
    """创建医生评价"""
    appointment_id: str = Field(..., description="预约ID")
    doctor_id: str = Field(..., description="医生ID")
    patient_id: str | None = Field(None, description="就诊人ID")
    rating: int = Field(..., ge=1, le=5, description="评分 1-5")
    content: str | None = Field(None, max_length=1000, description="评价内容")
    tags: list[str] | None = Field(None, description="评价标签")
    is_anonymous: bool = Field(False, description="是否匿名")


class DoctorReviewReply(BaseSchema):
    """回复评价"""
    reply: str = Field(..., min_length=1, max_length=500, description="回复内容")


class DoctorReviewResponse(BaseSchema):
    """评价响应"""
    id: str
    appointment_id: str | None = None
    doctor_id: str | None = None
    user_id: str | None = None
    patient_id: str | None = None
    rating: int | None = None
    content: str | None = None
    tags: list[str] | None = None
    is_anonymous: bool | None = None
    status: int | None = None
    reply: str | None = None
    reply_at: datetime | None = None
    created_at: datetime | None = None
    # 关联信息
    user_name: str | None = Field(None, description="评价用户名称")
    patient_name: str | None = Field(None, description="就诊人名称")
