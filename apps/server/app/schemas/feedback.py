from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from app.core.config import settings
from app.enums.feedback import FeedbackStatus, FeedbackType  # noqa: F401 — re-export
from app.schemas.media import normalize_media, publicize_media
from app.schemas.response import to_camel


class FeedbackCreate(BaseModel):
    """创建反馈"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    user_id: str = Field(..., description="用户ID")
    user_type: str = Field("patient", description="用户类型")
    feedback_type: str = Field("suggestion", description="反馈类型（字典: feedback_type）")
    title: str = Field(..., max_length=200, description="反馈标题")
    content: str = Field(..., min_length=10, description="反馈内容")
    images: list[str] | None = Field(None, description="图片URL列表")
    contact: str | None = Field(None, max_length=50, description="联系方式")

    @model_validator(mode="before")
    @classmethod
    def _normalize_media_paths(cls, data):
        # 客户端可能原样回写接口返回的绝对 URL，入口还原为相对路径
        return normalize_media(data)

class FeedbackReply(BaseModel):
    """回复反馈"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    reply: str = Field(..., min_length=1, description="回复内容")
    status: FeedbackStatus = Field(FeedbackStatus.RESOLVED, description="状态")

class FeedbackResponse(BaseModel):
    """反馈响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    user_id: str | None = None
    user_type: str | None = None
    feedback_type: str | None = None
    title: str | None = None
    content: str | None = None
    images: list[str] | None = None
    contact: str | None = None
    status: str | None = None
    handler_id: str | None = None
    reply: str | None = None
    handled_at: datetime | None = None
    created_at: datetime | None = None

    @field_serializer("images", when_used="json")
    def _publicize_images(self, value: list[str] | None) -> list[str] | None:
        return publicize_media(value)

class FeedbackQuery(BaseModel):
    """查询参数"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    user_id: str | None = None
    feedback_type: str | None = None
    status: FeedbackStatus | None = None
    keyword: str | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE)
