"""平台公告 Schema"""
from datetime import datetime
from json import loads as json_loads

from pydantic import Field, field_validator

from app.schemas.base import BaseRequestSchema, BaseSchema


class PlatformAnnouncementCreate(BaseRequestSchema):
    """创建平台公告"""

    title: str = Field(..., max_length=255, description="公告标题")
    content: str = Field(..., description="公告内容")
    target_type: str = Field(default="all", pattern="^(all|specific)$", description="目标类型")
    target_tenant_ids: list[str] | None = Field(None, description="指定租户ID列表")
    priority: int = Field(default=0, ge=0, le=2, description="优先级: 0-普通 1-重要 2-紧急")
    publish_at: datetime | None = Field(None, description="定时发布时间")
    expire_at: datetime | None = Field(None, description="过期时间")


class PlatformAnnouncementUpdate(BaseRequestSchema):
    """更新平台公告"""

    title: str | None = Field(None, max_length=255)
    content: str | None = None
    target_type: str | None = Field(None, pattern="^(all|specific)$")
    target_tenant_ids: list[str] | None = None
    priority: int | None = Field(None, ge=0, le=2)
    publish_at: datetime | None = None
    expire_at: datetime | None = None


class PlatformAnnouncementResponse(BaseSchema):
    """平台公告响应"""

    @field_validator("target_tenant_ids", mode="before")
    @classmethod
    def parse_target_tenant_ids(cls, v):
        if isinstance(v, str):
            try:
                return json_loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v

    id: str
    title: str
    content: str
    target_type: str
    target_tenant_ids: list[str] | None = None
    status: str
    priority: int
    publish_at: datetime | None = None
    expire_at: datetime | None = None
    publisher_id: str | None = None
    publisher_name: str | None = None
    read_count: int = 0
    total_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PlatformAnnouncementListResponse(BaseRequestSchema):
    """平台公告列表响应"""

    data: list[PlatformAnnouncementResponse] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
