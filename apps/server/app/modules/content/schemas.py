from app.schemas.response import to_camel

"""Content module DTOs."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NewsCreate(BaseModel):
    title: str = Field(..., max_length=200)
    type: int = Field(1, ge=1, le=4)
    cover_image: str | None = None
    summary: str | None = None
    content: str
    is_top: int = Field(0, ge=0, le=1)
    status: int = Field(0, ge=0, le=1)


class NewsResponse(BaseModel):
    id: str
    store_id: str | None = None
    title: str
    type: int
    cover_image: str | None = None
    summary: str | None = None
    content: str | None = None
    view_count: int = 0
    is_top: int = 0
    status: int = 0
    publish_time: datetime | None = None
    is_deleted: bool = False
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

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
    store_id: str | None = None
    title: str
    type: int
    content: str | None = None
    view_count: int = 0
    is_top: int = 0
    status: int = 0
    publish_time: datetime | None = None
    is_deleted: bool = False
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )


class BannerCreate(BaseModel):
    title: str | None = Field(None, max_length=100)
    image_url: str
    link_type: int = Field(0, ge=0, le=3)
    link_url: str | None = None
    position: str = "home"
    sort_order: int = Field(0, ge=0)
    status: int = Field(1, ge=0, le=1)


class BannerResponse(BaseModel):
    id: str
    store_id: str | None = None
    title: str | None = None
    image_url: str
    link_type: int = 0
    link_url: str | None = None
    position: str = "home"
    sort_order: int = 0
    status: int = 1
    is_deleted: bool = False
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

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
    operator_id: str | None = None
    snapshot: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,
    )


# ========== 批量操作 ==========
# BatchDeleteRequest / SortOrderItem 收敛至 app.schemas.common（行为等价）
from app.schemas.common import BatchDeleteRequest, SortOrderItem  # noqa: E402, F401


class BannerSortRequest(BaseModel):
    items: list[SortOrderItem] = Field(..., min_length=1, description="排序项列表")
