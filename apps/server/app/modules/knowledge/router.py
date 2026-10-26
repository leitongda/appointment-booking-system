"""知识库路由（prefix /knowledge 在 api/v1 注册；KB_ENABLED=false 时整体 404）

本文件：知识库 CRUD + 目录 + 语义检索；文档与共享见 router_documents（在此 include）。
权限码只判"能不能用这类功能"，对具体知识库的 owner/edit/read 级别在 service 内二次校验。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, require_admin_tenant_anchor, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.models.knowledge import KnowledgeBase
from app.modules.knowledge.router_documents import router as documents_router
from app.modules.knowledge.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
    KnowledgeFolderCreate,
    KnowledgeFolderResponse,
    KnowledgeFolderUpdate,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.modules.knowledge.service import KnowledgeService
from app.modules.knowledge.service_search import KnowledgeSearchService
from app.schemas.response import PageResponse


def require_kb_enabled() -> None:
    if not settings.KB_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库功能未启用")


router = APIRouter(dependencies=[Depends(require_kb_enabled)])


def _service(db: AsyncSession, current_admin: dict, tenant_anchor: str | None) -> KnowledgeService:
    return KnowledgeService(db, current_admin, tenant_anchor)


async def _base_response(
    service: KnowledgeService, kb: KnowledgeBase, permission: str | None = None
) -> KnowledgeBaseResponse:
    response = KnowledgeBaseResponse.model_validate(kb)
    response.my_permission = permission or await service.access.permission_for(kb)
    return response


# ==================== 知识库 ====================

@router.get("/bases", response_model=PageResponse[KnowledgeBaseResponse], summary="知识库列表")
async def list_bases(
    scope: str = Query("all", pattern="^(all|mine|shared|tenant)$", description="all/mine/shared/tenant"),
    keyword: str | None = Query(None, description="名称关键字"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:read")),
):
    service = _service(db, current_admin, tenant_anchor)
    rows, total = await service.list_bases(scope=scope, keyword=keyword, page=page, page_size=page_size)
    return PageResponse(
        data=[await _base_response(service, kb) for kb in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/bases", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED, summary="创建知识库")
async def create_base(
    data: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:create")),
):
    service = _service(db, current_admin, tenant_anchor)
    kb = await service.create_base(data)
    return await _base_response(service, kb, "owner")


@router.get("/bases/{kb_id}", response_model=KnowledgeBaseResponse, summary="知识库详情")
async def get_base(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:read")),
):
    service = _service(db, current_admin, tenant_anchor)
    kb, permission = await service.get_base(kb_id, "read")
    return await _base_response(service, kb, permission)


@router.patch("/bases/{kb_id}", response_model=KnowledgeBaseResponse, summary="更新知识库")
async def update_base(
    kb_id: str,
    data: KnowledgeBaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:update")),
):
    service = _service(db, current_admin, tenant_anchor)
    kb = await service.update_base(kb_id, data)
    return await _base_response(service, kb, "owner")


@router.delete("/bases/{kb_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除知识库（级联文档/切片/共享）")
async def delete_base(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:delete")),
):
    await _service(db, current_admin, tenant_anchor).delete_base(kb_id)


# ==================== 目录 ====================

@router.get(
    "/bases/{kb_id}/folders", response_model=list[KnowledgeFolderResponse], summary="目录列表（扁平，前端建树）"
)
async def list_folders(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:read")),
):
    folders = await _service(db, current_admin, tenant_anchor).list_folders(kb_id)
    return [KnowledgeFolderResponse.model_validate(folder) for folder in folders]


@router.post(
    "/bases/{kb_id}/folders",
    response_model=KnowledgeFolderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建目录",
)
async def create_folder(
    kb_id: str,
    data: KnowledgeFolderCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:update")),
):
    folder = await _service(db, current_admin, tenant_anchor).create_folder(kb_id, data)
    return KnowledgeFolderResponse.model_validate(folder)


@router.patch("/folders/{folder_id}", response_model=KnowledgeFolderResponse, summary="重命名/移动目录")
async def update_folder(
    folder_id: str,
    data: KnowledgeFolderUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:update")),
):
    folder = await _service(db, current_admin, tenant_anchor).update_folder(folder_id, data)
    return KnowledgeFolderResponse.model_validate(folder)


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除空目录")
async def delete_folder(
    folder_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:update")),
):
    await _service(db, current_admin, tenant_anchor).delete_folder(folder_id)


# ==================== 检索 ====================

@router.post(
    "/search", response_model=KnowledgeSearchResponse, summary="语义检索（范围 = 可见知识库，结果带引用来源）"
)
async def search(
    data: KnowledgeSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("knowledge:read")),
):
    service = KnowledgeSearchService(db, current_admin, tenant_anchor)
    return await service.search(data.query, data.kb_ids, data.top_k)


# 文档 + 共享（同一前缀、同一 KB_ENABLED 守卫）
router.include_router(documents_router)
