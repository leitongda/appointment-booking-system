from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class SupportTicketType(str, Enum):
    """工单类型"""

    SUGGESTION = "suggestion"
    COMPLAINT = "complaint"
    BUG = "bug"
    OTHER = "other"


class SupportTicketStatus(str, Enum):
    """工单状态"""

    PENDING = "pending"
    PROCESSING = "processing"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SupportTicketPriority(str, Enum):
    """工单优先级"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class SupportTicketCreate(BaseModel):
    """创建工单"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    title: str = Field(..., max_length=200, description="工单标题")
    description: str = Field(..., min_length=1, description="工单描述")
    type: SupportTicketType = Field(
        SupportTicketType.OTHER, description="工单类型"
    )
    priority: SupportTicketPriority = Field(
        SupportTicketPriority.MEDIUM, description="优先级"
    )
    contact_info: Optional[str] = Field(None, max_length=200, description="联系方式")
    attachments: Optional[List[str]] = Field(None, description="附件URL列表")


class SupportTicketUpdate(BaseModel):
    """更新工单"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    title: Optional[str] = Field(None, max_length=200, description="工单标题")
    description: Optional[str] = Field(None, description="工单描述")
    type: Optional[SupportTicketType] = Field(None, description="工单类型")
    priority: Optional[SupportTicketPriority] = Field(None, description="优先级")
    contact_info: Optional[str] = Field(None, max_length=200, description="联系方式")
    attachments: Optional[List[str]] = Field(None, description="附件URL列表")
    resolution: Optional[str] = Field(None, description="解决方案/备注")


class SupportTicketResponse(BaseModel):
    """工单响应"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )

    id: str
    tenant_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    creator_id: Optional[str] = None
    creator_type: Optional[str] = None
    assignee_id: Optional[str] = None
    contact_info: Optional[str] = None
    attachments: Optional[List[str]] = None
    resolution: Optional[str] = None
    closed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SupportTicketListResponse(BaseModel):
    """工单列表响应"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    data: List[SupportTicketResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = Field(default=10, alias="pageSize")


class SupportTicketQuery(BaseModel):
    """工单查询参数"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    status: Optional[SupportTicketStatus] = Field(None, description="状态")
    type: Optional[SupportTicketType] = Field(None, description="类型")
    priority: Optional[SupportTicketPriority] = Field(None, description="优先级")
    keyword: Optional[str] = Field(None, description="关键词搜索")
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=settings.MAX_PAGE_SIZE)


class SupportTicketAssignRequest(BaseModel):
    """分配工单请求"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    assignee_id: str = Field(..., description="处理人ID")


class SupportTicketResolveRequest(BaseModel):
    """解决工单请求"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    resolution: Optional[str] = Field(None, description="解决方案/备注")


class SupportTicketStatisticsResponse(BaseModel):
    """工单统计响应"""

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
