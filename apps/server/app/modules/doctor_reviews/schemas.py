from pydantic import Field
from typing import Optional, List
from datetime import datetime

from app.schemas.base import BaseSchema


class DoctorReviewCreate(BaseSchema):
    """创建医生评价"""
    appointment_id: str = Field(..., description="预约ID")
    doctor_id: str = Field(..., description="医生ID")
    patient_id: Optional[str] = Field(None, description="就诊人ID")
    rating: int = Field(..., ge=1, le=5, description="评分 1-5")
    content: Optional[str] = Field(None, max_length=1000, description="评价内容")
    tags: Optional[List[str]] = Field(None, description="评价标签")
    is_anonymous: bool = Field(False, description="是否匿名")


class DoctorReviewReply(BaseSchema):
    """回复评价"""
    reply: str = Field(..., min_length=1, max_length=500, description="回复内容")


class DoctorReviewResponse(BaseSchema):
    """评价响应"""
    id: str
    appointment_id: Optional[str] = None
    doctor_id: Optional[str] = None
    user_id: Optional[str] = None
    patient_id: Optional[str] = None
    rating: Optional[int] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    is_anonymous: Optional[bool] = None
    status: Optional[int] = None
    reply: Optional[str] = None
    reply_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    # 关联信息
    user_name: Optional[str] = Field(None, description="评价用户名称")
    patient_name: Optional[str] = Field(None, description="就诊人名称")
