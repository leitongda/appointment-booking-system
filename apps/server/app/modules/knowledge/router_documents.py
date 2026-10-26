"""知识库路由：文档（上传/详情/重命名/删除/重试/切片/下载）+ 共享授权

由 router.py include，共用其 KB_ENABLED 守卫与 /knowledge 前缀。
"""
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, require_admin_tenant_anchor, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.modules.knowledge.schemas import (
    KnowledgeChunkResponse,
    KnowledgeDocumentResponse,
    KnowledgeDocumentUpdate,
    KnowledgeShareCreate,
    KnowledgeShareResponse,
)
from app.modules.knowledge.service_documents import KnowledgeDocumentService
from app.schemas.response import PageResponse

router = APIRouter()


def _service(db: AsyncSession, current_admin: dict, tenant_anchor: str | None) -> KnowledgeDocumentService:
    return KnowledgeDocumentService(db, current_admin, tenant_anchor)


def _share_response(share, grantee_name: str | None) -> KnowledgeShareResponse:
    response = KnowledgeShareResponse.model_validate(share)
    response.grantee_name = grantee_name
    return response


# ==================== 文档 ====================

@router.get("/bases/{kb_id}/documents", response_model=PageResponse[KnowledgeDocumentResponse], summary="文档列表")
async def list_documents(
    kb_id: str,
    folder_id: str | None = Query(None, description="限定目录"),
    root_only: bool = Query(False, description="仅根目录下的文档（folder_id 为空时生效）"),
    doc_status: str | None = Query(None, alias="status", description="pending/parsing/embedding/ready/failed"),
    keyword: str | None = Query(None, description="标题/文件名关键字"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:read")),
):
    rows, total = await _service(db, current_admin, tenant_anchor).list_documents(
        kb_id,
        folder_id=folder_id,
        root_only=root_only,
        status=doc_status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        data=[KnowledgeDocumentResponse.model_validate(doc) for doc in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/bases/{kb_id}/documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="上传文档（pdf/docx/xlsx/txt/md，≤KB_MAX_FILE_MB）",
)
async def upload_document(
    kb_id: str,
    file: UploadFile = File(...),
    folder_id: str | None = Form(None),
    title: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:create")),
):
    service = _service(db, current_admin, tenant_anchor)
    doc = await service.upload_document(kb_id, file, folder_id=folder_id, title=title)
    return KnowledgeDocumentResponse.model_validate(doc)


@router.get("/documents/{doc_id}", response_model=KnowledgeDocumentResponse, summary="文档详情")
async def get_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:read")),
):
    doc, _kb = await _service(db, current_admin, tenant_anchor).get_document(doc_id, "read")
    return KnowledgeDocumentResponse.model_validate(doc)


@router.patch("/documents/{doc_id}", response_model=KnowledgeDocumentResponse, summary="重命名/移动文档")
async def update_document(
    doc_id: str,
    data: KnowledgeDocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:update")),
):
    doc = await _service(db, current_admin, tenant_anchor).update_document(doc_id, data)
    return KnowledgeDocumentResponse.model_validate(doc)


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除文档（含切片与原件）")
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:delete")),
):
    await _service(db, current_admin, tenant_anchor).delete_document(doc_id)


@router.post("/documents/{doc_id}/retry", response_model=KnowledgeDocumentResponse, summary="重新处理失败文档")
async def retry_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:update")),
):
    doc = await _service(db, current_admin, tenant_anchor).retry_document(doc_id)
    return KnowledgeDocumentResponse.model_validate(doc)


@router.get(
    "/documents/{doc_id}/chunks",
    response_model=PageResponse[KnowledgeChunkResponse],
    summary="文档切片（抽取文本预览）",
)
async def list_chunks(
    doc_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:read")),
):
    rows, total = await _service(db, current_admin, tenant_anchor).list_chunks(doc_id, page=page, page_size=page_size)
    return PageResponse(
        data=[KnowledgeChunkResponse.model_validate(chunk) for chunk in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/documents/{doc_id}/file", summary="下载 / 预览原件（租户 + 可见性校验，key 不暴露）")
async def download_document(
    doc_id: str,
    download: bool = Query(False, description="true=附件下载，false=内联预览"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:read")),
):
    doc, path, url = await _service(db, current_admin, tenant_anchor).resolve_document_file(doc_id)
    if url:
        return RedirectResponse(url)
    disposition = "attachment" if download else "inline"
    return FileResponse(
        path=str(path),
        media_type=doc.mime_type,
        headers={
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(doc.file_name)}",
            "Cache-Control": "private, max-age=0",
        },
    )


# ==================== 共享 ====================

@router.get("/bases/{kb_id}/shares", response_model=list[KnowledgeShareResponse], summary="共享列表")
async def list_shares(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:share")),
):
    rows = await _service(db, current_admin, tenant_anchor).list_shares(kb_id)
    return [_share_response(share, name) for share, name in rows]


@router.post(
    "/bases/{kb_id}/shares",
    response_model=KnowledgeShareResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新增/更新共享",
)
async def add_share(
    kb_id: str,
    data: KnowledgeShareCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:share")),
):
    share, name = await _service(db, current_admin, tenant_anchor).add_share(kb_id, data)
    return _share_response(share, name)


@router.delete("/shares/{share_id}", status_code=status.HTTP_204_NO_CONTENT, summary="撤销共享")
async def remove_share(
    share_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:share")),
):
    await _service(db, current_admin, tenant_anchor).remove_share(share_id)
