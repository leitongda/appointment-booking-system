from app.schemas.response import to_camel
"""Content module DTOs."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class NewsCreate(BaseModel):
    title: str = Field(..., max_length=200)
    type: int = Field(1, ge=1, le=4)
    cover_image: Optional[str] = None
    summary: Optional[str] = None
    content: str
    is_top: int = Field(0, ge=0, le=1)
    status: int = Field(0, ge=0, le=1)


class NewsResponse(BaseModel):
    id: str
    store_id: Optional[str] = None
    title: str
    type: int
    cover_image: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    view_count: int = 0
    is_top: int = 0
    status: int = 0
    publish_time: Optional[datetime] = None
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )


class NoticeCreate(BaseModel):
    title: str = Field(..., max_length=200)
    type: int = Field(1, ge=1, le=4)
    content: str
    is_top: int = Field(0, ge=0, le=1)
    status: int = Field(0, ge=0, le=1)


class NoticeResponse(BaseModel):
    id: str
    store_id: Optional[str] = None
    title: str
    type: int
    content: Optional[str] = None
    view_count: int = 0
    is_top: int = 0
    status: int = 0
    publish_time: Optional[datetime] = None
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )


class BannerCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    image_url: str
    link_type: int = Field(0, ge=0, le=3)
    link_url: Optional[str] = None
    position: str = "home"
    sort_order: int = Field(0, ge=0)
    status: int = Field(1, ge=0, le=1)


class BannerResponse(BaseModel):
    id: str
    store_id: Optional[str] = None
    title: Optional[str] = None
    image_url: str
    link_type: int = 0
    link_url: Optional[str] = None
    position: str = "home"
    sort_order: int = 0
    status: int = 1
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )


# ========== 版本历史 ==========

class ContentVersionResponse(BaseModel):
    id: str
    content_type: str
    content_id: str
    operator_id: Optional[str] = None
    snapshot: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )


# ========== 批量操作 ==========

class BatchDeleteRequest(BaseModel):
    ids: List[str] = Field(..., min_length=1, description="要删除的ID列表")


class SortOrderItem(BaseModel):
    id: str
    sort_order: int = Field(..., ge=0)


class BannerSortRequest(BaseModel):
    items: List[SortOrderItem] = Field(..., min_length=1, description="排序项列表")
