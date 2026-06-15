"""平台公告 Schema"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.response import to_camel


class PlatformAnnouncementCreate(BaseModel):
    """创建平台公告"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    title: str = Field(..., max_length=255, description="公告标题")
    content: str = Field(..., description="公告内容")
    target_type: str = Field(default="all", pattern="^(all|specific)$", description="目标类型")
    target_tenant_ids: list[str] | None = Field(None, description="指定租户ID列表")
    priority: int = Field(default=0, ge=0, le=2, description="优先级: 0-普通 1-重要 2-紧急")
    publish_at: datetime | None = Field(None, description="定时发布时间")
    expire_at: datetime | None = Field(None, description="过期时间")


class PlatformAnnouncementUpdate(BaseModel):
    """更新平台公告"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    title: str | None = Field(None, max_length=255)
    content: str | None = None
    target_type: str | None = Field(None, pattern="^(all|specific)$")
    target_tenant_ids: list[str] | None = None
    priority: int | None = Field(None, ge=0, le=2)
    publish_at: datetime | None = None
    expire_at: datetime | None = None


class PlatformAnnouncementResponse(BaseModel):
    """平台公告响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )

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


class PlatformAnnouncementListResponse(BaseModel):
    """平台公告列表响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    data: list[PlatformAnnouncementResponse] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
