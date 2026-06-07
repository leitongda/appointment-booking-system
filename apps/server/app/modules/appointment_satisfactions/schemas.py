from pydantic import Field
from typing import Optional, List
from datetime import datetime

from app.schemas.base import BaseSchema


class AppointmentSatisfactionCreate(BaseSchema):
    """创建预约满意度"""
    overall_score: int = Field(..., ge=1, le=5, description="综合评分 1-5")
    service_score: Optional[int] = Field(None, ge=1, le=5, description="服务态度评分 1-5")
    environment_score: Optional[int] = Field(None, ge=1, le=5, description="环境评分 1-5")
    comment: Optional[str] = Field(None, max_length=500, description="评价内容")
    tags: Optional[List[str]] = Field(None, description="评价标签")


class AppointmentSatisfactionResponse(BaseSchema):
    """满意度响应"""
    id: str
    appointment_id: Optional[str] = None
    user_id: Optional[str] = None
    patient_id: Optional[str] = None
    doctor_id: Optional[str] = None
    overall_score: Optional[int] = None
    service_score: Optional[int] = None
    environment_score: Optional[int] = None
    comment: Optional[str] = None
    tags: Optional[List[str]] = None
    submitted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
