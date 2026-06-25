"""CMS module DTOs (站点 / 栏目 / 文章)."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.response import to_camel

# 统一 Response 配置：ORM 模式 + camelCase 别名
_RESPONSE_CONFIG = ConfigDict(
    from_attributes=True,
    populate_by_name=True,
    alias_generator=to_camel,
    by_alias=True,
)


# ============================================================
# 站点 Site
# ============================================================

class SiteCreate(BaseModel):
    name: str = Field(..., max_length=100, description="站点名称")
    code: str = Field(..., max_length=50, description="站点编码")
    description: str | None = Field(None, max_length=500)
    domain: str | None = Field(None, max_length=200)
    logo_url: str | None = Field(None, max_length=500)
    favicon_url: str | None = Field(None, max_length=500)
    theme_config: dict[str, Any] | None = None
    seo_config: dict[str, Any] | None = None
    status: int = Field(1, ge=0, le=1)
    is_default: int = Field(0, ge=0, le=1)


class SiteUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=500)
    domain: str | None = Field(None, max_length=200)
    logo_url: str | None = Field(None, max_length=500)
    favicon_url: str | None = Field(None, max_length=500)
    theme_config: dict[str, Any] | None = None
    seo_config: dict[str, Any] | None = None
    status: int | None = Field(None, ge=0, le=1)
    is_default: int | None = Field(None, ge=0, le=1)


class SiteResponse(BaseModel):
    id: str
    tenant_id: str | None = None
    name: str
    code: str
    description: str | None = None
    domain: str | None = None
    logo_url: str | None = None
    favicon_url: str | None = None
    theme_config: dict[str, Any] | None = None
    seo_config: dict[str, Any] | None = None
    status: int = 1
    is_default: int = 0
    is_deleted: bool = False
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = _RESPONSE_CONFIG


# ============================================================
# 栏目 Category
# ============================================================

class CategoryCreate(BaseModel):
    site_id: str = Field(..., description="所属站点ID")
    name: str = Field(..., max_length=100)
    slug: str = Field(..., max_length=100)
    parent_id: str | None = None
    sort_order: int = Field(0, ge=0)
    icon: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=500)
    status: int = Field(1, ge=0, le=1)


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    parent_id: str | None = None
    sort_order: int | None = Field(None, ge=0)
    icon: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=500)
    status: int | None = Field(None, ge=0, le=1)


class CategoryResponse(BaseModel):
    id: str
    tenant_id: str | None = None
    site_id: str
    name: str
    slug: str
    parent_id: str | None = None
    sort_order: int = 0
    icon: str | None = None
    description: str | None = None
    status: int = 1
    is_deleted: bool = False
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = _RESPONSE_CONFIG


class CategoryTreeNode(CategoryResponse):
    """栏目树节点（带 children）"""
    children: list["CategoryTreeNode"] = []


# ============================================================
# 文章 Article
# ============================================================

class ArticleCreate(BaseModel):
    site_id: str = Field(..., description="所属站点ID")
    category_id: str | None = None
    title: str = Field(..., max_length=200)
    subtitle: str | None = Field(None, max_length=200)
    slug: str | None = Field(None, max_length=200)
    cover_image: str | None = Field(None, max_length=500)
    summary: str | None = Field(None, max_length=500)
    content: str
    author: str | None = Field(None, max_length=50)
    source: str | None = Field(None, max_length=100)
    tags: list[str] | None = None
    sort_order: int = Field(0, ge=0)
    is_top: int = Field(0, ge=0, le=1)
    status: int = Field(0, ge=0, le=2)
    store_id: str | None = None
    seo_title: str | None = Field(None, max_length=200)
    seo_keywords: str | None = Field(None, max_length=500)
    seo_description: str | None = Field(None, max_length=500)


class ArticleUpdate(BaseModel):
    category_id: str | None = None
    title: str | None = Field(None, max_length=200)
    subtitle: str | None = Field(None, max_length=200)
    slug: str | None = Field(None, max_length=200)
    cover_image: str | None = Field(None, max_length=500)
    summary: str | None = Field(None, max_length=500)
    content: str | None = None
    author: str | None = Field(None, max_length=50)
    source: str | None = Field(None, max_length=100)
    tags: list[str] | None = None
    sort_order: int | None = Field(None, ge=0)
    is_top: int | None = Field(None, ge=0, le=1)
    status: int | None = Field(None, ge=0, le=2)
    store_id: str | None = None
    seo_title: str | None = Field(None, max_length=200)
    seo_keywords: str | None = Field(None, max_length=500)
    seo_description: str | None = Field(None, max_length=500)


class ArticleResponse(BaseModel):
    id: str
    tenant_id: str | None = None
    site_id: str
    store_id: str | None = None
    category_id: str | None = None
    title: str
    subtitle: str | None = None
    slug: str | None = None
    cover_image: str | None = None
    summary: str | None = None
    content: str | None = None
    author: str | None = None
    source: str | None = None
    tags: list[str] | None = None
    sort_order: int = 0
    is_top: int = 0
    status: int = 0
    publish_time: datetime | None = None
    view_count: int = 0
    seo_title: str | None = None
    seo_keywords: str | None = None
    seo_description: str | None = None
    is_deleted: bool = False
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = _RESPONSE_CONFIG


# ============================================================
# 通用：批量删除 / 排序
# ============================================================

class BatchDeleteRequest(BaseModel):
    ids: list[str] = Field(..., min_length=1, description="要删除的ID列表")


class SortOrderItem(BaseModel):
    id: str
    sort_order: int = Field(..., ge=0)


class SortOrderRequest(BaseModel):
    items: list[SortOrderItem] = Field(..., min_length=1, description="排序项列表")
