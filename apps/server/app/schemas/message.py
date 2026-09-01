from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.enums.message import MessageType  # noqa: F401 — re-export
from app.schemas.base import BaseRequestSchema, BaseSchema
from app.schemas.response import to_camel


class MessageBase(BaseRequestSchema):
    """消息基础模型"""

    title: str = Field(..., max_length=200, description="消息标题")
    content: str | None = Field(None, description="消息内容")
    message_type: str = Field("system", description="消息类型（字典: message_type）")
    related_id: str | None = Field(None, description="关联业务ID")

class MessageCreate(MessageBase):
    """创建消息"""
    user_id: str = Field(..., description="接收用户ID")
    user_type: str = Field(..., description="用户类型: patient/doctor")
    extra_data: dict | None = Field(None, description="额外数据")

class MessageBatchCreate(BaseRequestSchema):
    """批量创建消息"""

    user_ids: list[str] = Field(..., description="接收用户ID列表")
    user_type: str = Field(..., description="用户类型")
    title: str = Field(..., max_length=200)
    content: str | None = None
    message_type: str = "system"
    related_id: str | None = None

class MessageResponse(BaseSchema):
    """消息响应"""

    id: str
    store_id: str | None = None
    user_id: str | None = None
    user_type: str | None = None
    title: str | None = None
    content: str | None = None
    message_type: str | None = None
    related_id: str | None = None
    is_read: int | None = 0
    read_at: datetime | None = None
    created_at: datetime | None = None

class MessageListResponse(BaseSchema):
    """消息列表响应"""

    id: str
    store_id: str | None = None
    title: str | None = None
    content: str | None = None
    message_type: str | None = None
    is_read: int | None = 0
    created_at: datetime | None = None

class MessageQuery(BaseRequestSchema):
    """消息查询参数"""

    message_type: str | None = Field(None, description="消息类型（字典: message_type）")
    is_read: int | None = Field(None, description="是否已读")
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
class MessageTemplateBase(BaseRequestSchema):

    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    message_type: str
    title_template: str = Field(..., max_length=200)
    content_template: str
    description: str | None = Field(None, max_length=255)
    status: int = Field(1, ge=0, le=1)

class MessageTemplateCreate(MessageTemplateBase):
    pass

class MessageTemplateUpdate(BaseRequestSchema):

    name: str | None = Field(None, max_length=100)
    title_template: str | None = Field(None, max_length=200)
    content_template: str | None = None
    description: str | None = Field(None, max_length=255)
    status: int | None = Field(None, ge=0, le=1)

class MessageTemplateResponse(BaseSchema):
    """消息模板响应"""

    id: str
    code: str | None = None
    name: str | None = None
    message_type: str | None = None
    title_template: str | None = None
    content_template: str | None = None
    description: str | None = None
    status: int | None = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
