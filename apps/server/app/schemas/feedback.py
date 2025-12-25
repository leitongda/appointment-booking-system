from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class FeedbackType(str, Enum):
    SUGGESTION = "suggestion"
    COMPLAINT = "complaint"
    BUG = "bug"
    OTHER = "other"


class FeedbackStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    RESOLVED = "resolved"
    CLOSED = "closed"


class FeedbackCreate(BaseModel):
    """创建反馈"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    user_id: str = Field(..., description="用户ID")
    user_type: str = Field("patient", description="用户类型")
    feedback_type: FeedbackType = Field(FeedbackType.SUGGESTION, description="反馈类型")
    title: str = Field(..., max_length=200, description="反馈标题")
    content: str = Field(..., min_length=10, description="反馈内容")
    images: Optional[List[str]] = Field(None, description="图片URL列表")
    contact: Optional[str] = Field(None, max_length=50, description="联系方式")


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
    user_id: Optional[str] = None
    user_type: Optional[str] = None
    feedback_type: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    images: Optional[List[str]] = None
    contact: Optional[str] = None
    status: Optional[str] = None
    handler_id: Optional[str] = None
    reply: Optional[str] = None
    handled_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class FeedbackQuery(BaseModel):
    """查询参数"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    user_id: Optional[str] = None
    feedback_type: Optional[FeedbackType] = None
    status: Optional[FeedbackStatus] = None
    keyword: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
