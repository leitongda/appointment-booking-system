from datetime import datetime

from pydantic import Field

from app.schemas.base import BaseSchema


class AppointmentSatisfactionCreate(BaseSchema):
    """创建预约满意度"""
    overall_score: int = Field(..., ge=1, le=5, description="综合评分 1-5")
    service_score: int | None = Field(None, ge=1, le=5, description="服务态度评分 1-5")
    environment_score: int | None = Field(None, ge=1, le=5, description="环境评分 1-5")
    comment: str | None = Field(None, max_length=500, description="评价内容")
    tags: list[str] | None = Field(None, description="评价标签")


class AppointmentSatisfactionResponse(BaseSchema):
    """满意度响应"""
    id: str
    appointment_id: str | None = None
    user_id: str | None = None
    patient_id: str | None = None
    doctor_id: str | None = None
    overall_score: int | None = None
    service_score: int | None = None
    environment_score: int | None = None
    comment: str | None = None
    tags: list[str] | None = None
    submitted_at: datetime | None = None
    created_at: datetime | None = None
