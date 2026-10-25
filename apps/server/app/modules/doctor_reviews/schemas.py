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


class DoctorReviewPatientCreate(BaseSchema):
    """患者端创建医生评价

    appointment_id 可选：缺省时服务端自动关联该患者在此医生下的
    最近一次预约（评价表 appointment_id 非空，见 app/models/doctor_review.py）。
    """
    doctor_id: str = Field(..., description="医生ID")
    rating: int = Field(..., ge=1, le=5, description="评分 1-5")
    content: str = Field(..., min_length=1, max_length=1000, description="评价内容")
    appointment_id: str | None = Field(None, description="预约ID（可选，缺省取最近一次预约）")
    is_anonymous: bool = Field(False, description="是否匿名")


class DoctorReviewPatientItem(BaseSchema):
    """患者端评价列表项（就诊人姓名脱敏）"""
    id: str
    doctor_id: str | None = None
    rating: int | None = None
    content: str | None = None
    tags: list[str] | None = None
    reply: str | None = None
    reply_at: datetime | None = None
    created_at: datetime | None = None
    patient_name: str | None = Field(None, description="就诊人姓名（脱敏，如 雷**）")


class DoctorReviewPatientListResponse(BaseSchema):
    """患者端评价列表"""
    items: list[DoctorReviewPatientItem] = Field(default_factory=list, description="评价列表")
    total: int = Field(0, description="总数")


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
