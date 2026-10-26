"""知识库 Schemas"""
from datetime import datetime

from pydantic import Field

from app.enums.knowledge import (
    KnowledgeShareGrantee,
    KnowledgeSharePermission,
    KnowledgeVisibility,
)
from app.schemas.base import BaseRequestSchema, BaseSchema

# ---------- 知识库 ----------

class KnowledgeBaseCreate(BaseRequestSchema):
    name: str = Field(..., min_length=1, max_length=100, description="名称")
    description: str | None = Field(None, max_length=2000, description="描述")
    visibility: KnowledgeVisibility = Field(KnowledgeVisibility.PRIVATE, description="可见性")


class KnowledgeBaseUpdate(BaseRequestSchema):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=2000)
    visibility: KnowledgeVisibility | None = None


class KnowledgeBaseResponse(BaseSchema):
    id: str
    tenant_id: str | None = None
    name: str
    description: str | None = None
    owner_admin_id: str
    visibility: str
    embedding_model: str
    embedding_dims: int
    doc_count: int = 0
    chunk_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    my_permission: str | None = Field(None, description="当前用户对该库的权限级别: owner/edit/read")


# ---------- 目录 ----------

class KnowledgeFolderCreate(BaseRequestSchema):
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: str | None = None
    sort_order: int = 0


class KnowledgeFolderUpdate(BaseRequestSchema):
    """parent_id 显式传 null 表示移到根目录；不传表示不改"""
    name: str | None = Field(None, min_length=1, max_length=100)
    parent_id: str | None = None
    sort_order: int | None = None


class KnowledgeFolderResponse(BaseSchema):
    id: str
    kb_id: str
    parent_id: str | None = None
    name: str
    sort_order: int = 0
    created_at: datetime | None = None


# ---------- 文档 ----------

class KnowledgeDocumentUpdate(BaseRequestSchema):
    """folder_id 显式传 null 表示移到根目录；不传表示不改"""
    title: str | None = Field(None, min_length=1, max_length=200)
    folder_id: str | None = None


class KnowledgeDocumentResponse(BaseSchema):
    id: str
    kb_id: str
    folder_id: str | None = None
    title: str
    file_name: str
    mime_type: str
    size_bytes: int = 0
    status: str
    failed_stage: str | None = None
    error_message: str | None = None
    page_count: int | None = None
    chunk_count: int = 0
    uploaded_by: str | None = None
    processed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class KnowledgeChunkResponse(BaseSchema):
    id: str
    doc_id: str
    seq: int
    content: str
    page_no: int | None = None
    section: str | None = None
    token_count: int = 0


# ---------- 共享 ----------

class KnowledgeShareCreate(BaseRequestSchema):
    grantee_type: KnowledgeShareGrantee
    grantee_id: str = Field(..., min_length=1, max_length=36)
    permission: KnowledgeSharePermission = KnowledgeSharePermission.READ


class KnowledgeShareResponse(BaseSchema):
    id: str
    kb_id: str
    grantee_type: str
    grantee_id: str
    grantee_name: str | None = None
    permission: str
    granted_by: str | None = None
    created_at: datetime | None = None


# ---------- 检索 ----------

class KnowledgeSearchRequest(BaseRequestSchema):
    query: str = Field(..., min_length=1, max_length=1000, description="查询文本")
    kb_ids: list[str] | None = Field(None, description="限定知识库；不传=全部可见库")
    top_k: int = Field(8, ge=1, description="返回条数，上限见 KB_SEARCH_TOP_K_MAX")


class KnowledgeSearchHit(BaseSchema):
    chunk_id: str
    doc_id: str
    doc_title: str
    kb_id: str
    page_no: int | None = None
    section: str | None = None
    snippet: str
    score: float
    preview_url: str


class KnowledgeSearchResponse(BaseSchema):
    hits: list[KnowledgeSearchHit]
    total: int
    took_ms: int
