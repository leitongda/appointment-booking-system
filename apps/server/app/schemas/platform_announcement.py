"""平台公告 Schema"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

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
    target_tenant_ids: Optional[List[str]] = Field(None, description="指定租户ID列表")
    priority: int = Field(default=0, ge=0, le=2, description="优先级: 0-普通 1-重要 2-紧急")
    publish_at: Optional[datetime] = Field(None, description="定时发布时间")
    expire_at: Optional[datetime] = Field(None, description="过期时间")


class PlatformAnnouncementUpdate(BaseModel):
    """更新平台公告"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    target_type: Optional[str] = Field(None, pattern="^(all|specific)$")
    target_tenant_ids: Optional[List[str]] = None
    priority: Optional[int] = Field(None, ge=0, le=2)
    publish_at: Optional[datetime] = None
    expire_at: Optional[datetime] = None


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
    target_tenant_ids: Optional[List[str]] = None
    status: str
    priority: int
    publish_at: Optional[datetime] = None
    expire_at: Optional[datetime] = None
    publisher_id: Optional[str] = None
    publisher_name: Optional[str] = None
    read_count: int = 0
    total_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PlatformAnnouncementListResponse(BaseModel):
    """平台公告列表响应"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    data: List[PlatformAnnouncementResponse] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
