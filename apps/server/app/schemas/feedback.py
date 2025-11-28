from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


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
    user_id: str = Field(..., description="用户ID")
    user_type: str = Field("patient", description="用户类型")
    feedback_type: FeedbackType = Field(FeedbackType.SUGGESTION, description="反馈类型")
    title: str = Field(..., max_length=200, description="反馈标题")
    content: str = Field(..., min_length=10, description="反馈内容")
    images: Optional[List[str]] = Field(None, description="图片URL列表")
    contact: Optional[str] = Field(None, max_length=50, description="联系方式")


class FeedbackReply(BaseModel):
    """回复反馈"""
    reply: str = Field(..., min_length=1, description="回复内容")
    status: FeedbackStatus = Field(FeedbackStatus.RESOLVED, description="状态")


class FeedbackResponse(BaseModel):
    """反馈响应"""
    id: str
    user_id: str
    user_type: str
    feedback_type: str
    title: str
    content: str
    images: Optional[List[str]] = None
    contact: Optional[str]
    status: str
    handler_id: Optional[str]
    reply: Optional[str]
    handled_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class FeedbackQuery(BaseModel):
    """查询参数"""
    user_id: Optional[str] = None
    feedback_type: Optional[FeedbackType] = None
    status: Optional[FeedbackStatus] = None
    keyword: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
