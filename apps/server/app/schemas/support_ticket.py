from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.enums.support_ticket import (  # noqa: F401 — re-export
    SupportTicketPriority,
    SupportTicketStatus,
    SupportTicketType,
)
from app.schemas.base import BaseRequestSchema, BaseSchema
from app.schemas.response import to_camel


class SupportTicketCreate(BaseRequestSchema):
    """创建工单"""

    title: str = Field(..., max_length=200, description="工单标题")
    description: str = Field(..., min_length=1, description="工单描述")
    type: str = Field("other", description="工单类型（字典: support_ticket_type）")
    priority: str = Field("medium", description="优先级（字典: support_ticket_priority）")
    contact_info: str | None = Field(None, max_length=200, description="联系方式")
    attachments: list[str] | None = Field(None, description="附件URL列表")

class SupportTicketUpdate(BaseRequestSchema):
    """更新工单"""

    title: str | None = Field(None, max_length=200, description="工单标题")
    description: str | None = Field(None, description="工单描述")
    type: str | None = Field(None, description="工单类型（字典: support_ticket_type）")
    priority: str | None = Field(None, description="优先级（字典: support_ticket_priority）")
    contact_info: str | None = Field(None, max_length=200, description="联系方式")
    attachments: list[str] | None = Field(None, description="附件URL列表")
    resolution: str | None = Field(None, description="解决方案/备注")

class SupportTicketResponse(BaseSchema):
    """工单响应"""

    id: str
    tenant_id: str | None = None
    title: str | None = None
    description: str | None = None
    type: str | None = None
    status: str | None = None
    priority: str | None = None
    creator_id: str | None = None
    creator_type: str | None = None
    assignee_id: str | None = None
    contact_info: str | None = None
    attachments: list[str] | None = None
    resolution: str | None = None
    closed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class SupportTicketListResponse(BaseModel):
    """工单列表响应
    NOTE: 原 ConfigDict 为 {alias_generator, populate_by_name, by_alias=True}（3 字段，无 from_attributes），
    与 BaseSchema（4 字段）不一致，保留手写配置避免行为变化。
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    data: list[SupportTicketResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = Field(default=10, alias="pageSize")

class SupportTicketQuery(BaseRequestSchema):
    """工单查询参数"""

    status: SupportTicketStatus | None = Field(None, description="状态")
    type: str | None = Field(None, description="类型（字典: support_ticket_type）")
    priority: str | None = Field(None, description="优先级（字典: support_ticket_priority）")
    keyword: str | None = Field(None, description="关键词搜索")
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE)

class SupportTicketAssignRequest(BaseRequestSchema):
    """分配工单请求"""

    assignee_id: str = Field(..., description="处理人ID")

class SupportTicketResolveRequest(BaseRequestSchema):
    """解决工单请求"""

    resolution: str | None = Field(None, description="解决方案/备注")

class SupportTicketStatisticsResponse(BaseModel):
    """工单统计响应
    NOTE: 原 ConfigDict 为 {alias_generator, populate_by_name, by_alias=True}（3 字段，无 from_attributes），
    与 BaseSchema（4 字段）不一致，保留手写配置避免行为变化。
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    total: int = 0
    pending: int = 0
    processing: int = 0
    resolved: int = 0
    closed: int = 0
