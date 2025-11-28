from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    APPOINTMENT = "appointment"
    CONSULTATION = "consultation"
    SCHEDULE = "schedule"
    SYSTEM = "system"
    STOP_CLINIC = "stop_clinic"


class MessageBase(BaseModel):
    """消息基础模型"""
    title: str = Field(..., max_length=200, description="消息标题")
    content: Optional[str] = Field(None, description="消息内容")
    message_type: MessageType = Field(MessageType.SYSTEM, description="消息类型")
    related_id: Optional[str] = Field(None, description="关联业务ID")


class MessageCreate(MessageBase):
    """创建消息"""
    user_id: str = Field(..., description="接收用户ID")
    user_type: str = Field(..., description="用户类型: patient/doctor")
    extra_data: Optional[dict] = Field(None, description="额外数据")


class MessageBatchCreate(BaseModel):
    """批量创建消息"""
    user_ids: List[str] = Field(..., description="接收用户ID列表")
    user_type: str = Field(..., description="用户类型")
    title: str = Field(..., max_length=200)
    content: Optional[str] = None
    message_type: MessageType = MessageType.SYSTEM
    related_id: Optional[str] = None


class MessageResponse(MessageBase):
    """消息响应"""
    id: str
    user_id: str
    user_type: str
    is_read: int
    read_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """消息列表响应"""
    id: str
    title: str
    content: Optional[str]
    message_type: str
    is_read: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class MessageQuery(BaseModel):
    """消息查询参数"""
    message_type: Optional[MessageType] = Field(None, description="消息类型")
    is_read: Optional[int] = Field(None, description="是否已读")
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)


class UnreadCountResponse(BaseModel):
    """未读消息数量"""
    total: int = 0
    appointment: int = 0
    consultation: int = 0
    schedule: int = 0
    system: int = 0
    stop_clinic: int = 0


# 消息模板
class MessageTemplateBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    message_type: MessageType
    title_template: str = Field(..., max_length=200)
    content_template: str
    description: Optional[str] = Field(None, max_length=255)
    status: int = Field(1, ge=0, le=1)


class MessageTemplateCreate(MessageTemplateBase):
    pass


class MessageTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    title_template: Optional[str] = Field(None, max_length=200)
    content_template: Optional[str] = None
    description: Optional[str] = Field(None, max_length=255)
    status: Optional[int] = Field(None, ge=0, le=1)


class MessageTemplateResponse(MessageTemplateBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
