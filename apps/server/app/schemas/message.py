from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Any
from datetime import datetime

from app.enums.message import MessageType  # noqa: F401 — re-export
from app.core.config import settings
from app.schemas.response import to_camel

class MessageBase(BaseModel):
    """消息基础模型"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    title: str = Field(..., max_length=200, description="消息标题")
    content: Optional[str] = Field(None, description="消息内容")
    message_type: str = Field("system", description="消息类型（字典: message_type）")
    related_id: Optional[str] = Field(None, description="关联业务ID")

class MessageCreate(MessageBase):
    """创建消息"""
    user_id: str = Field(..., description="接收用户ID")
    user_type: str = Field(..., description="用户类型: patient/doctor")
    extra_data: Optional[dict] = Field(None, description="额外数据")

class MessageBatchCreate(BaseModel):
    """批量创建消息"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    user_ids: List[str] = Field(..., description="接收用户ID列表")
    user_type: str = Field(..., description="用户类型")
    title: str = Field(..., max_length=200)
    content: Optional[str] = None
    message_type: str = "system"
    related_id: Optional[str] = None

class MessageResponse(BaseModel):
    """消息响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    store_id: Optional[str] = None
    user_id: Optional[str] = None
    user_type: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    message_type: Optional[str] = None
    related_id: Optional[str] = None
    is_read: Optional[int] = 0
    read_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

class MessageListResponse(BaseModel):
    """消息列表响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    store_id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    message_type: Optional[str] = None
    is_read: Optional[int] = 0
    created_at: Optional[datetime] = None

class MessageQuery(BaseModel):
    """消息查询参数"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    message_type: Optional[str] = Field(None, description="消息类型（字典: message_type）")
    is_read: Optional[int] = Field(None, description="是否已读")
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE)

class UnreadCountResponse(BaseModel):
    """未读消息数量"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )
    
    total: int = 0
    appointment: int = 0
    consultation: int = 0
    schedule: int = 0
    system: int = 0
    stop_clinic: int = 0
    feedback: int = 0

# 消息模板
class MessageTemplateBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    message_type: str
    title_template: str = Field(..., max_length=200)
    content_template: str
    description: Optional[str] = Field(None, max_length=255)
    status: int = Field(1, ge=0, le=1)

class MessageTemplateCreate(MessageTemplateBase):
    pass

class MessageTemplateUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    
    name: Optional[str] = Field(None, max_length=100)
    title_template: Optional[str] = Field(None, max_length=200)
    content_template: Optional[str] = None
    description: Optional[str] = Field(None, max_length=255)
    status: Optional[int] = Field(None, ge=0, le=1)

class MessageTemplateResponse(BaseModel):
    """消息模板响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )
    
    id: str
    code: Optional[str] = None
    name: Optional[str] = None
    message_type: Optional[str] = None
    title_template: Optional[str] = None
    content_template: Optional[str] = None
    description: Optional[str] = None
    status: Optional[int] = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
