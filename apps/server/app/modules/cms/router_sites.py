"""CMS 站点管理路由"""

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.modules.cms.schemas import (
    BatchDeleteRequest,
    SiteCreate,
    SiteResponse,
    SiteUpdate,
)
from app.modules.cms.service import CmsSiteService
from app.schemas.response import PageResponse
from app.utils.audit import get_operator_id_from_admin

router = APIRouter()


def _to_response(site) -> SiteResponse:
    """序列化站点，把 JSON 文本字段还原为 dict"""
    payload = {c.name: getattr(site, c.name) for c in site.__table__.columns}
    for key in ("theme_config", "seo_config"):
        raw = payload.get(key)
        if isinstance(raw, str) and raw:
            try:
                payload[key] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                payload[key] = None
    return SiteResponse.model_validate(payload)


@router.get("", response_model=PageResponse[SiteResponse], summary="获取站点列表")
async def list_sites(
    keyword: str | None = None,
    site_status: int | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:site", "cms:site:create", "cms:site:update", "cms:site:delete")),
):
    service = CmsSiteService(db)
    items, total = await service.get_list(
        tenant_id=current_admin["tenant_id"],
        keyword=keyword,
        status=site_status,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        data=[_to_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{site_id}", response_model=SiteResponse, summary="获取站点详情")
async def get_site(
    site_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:site")),
):
    service = CmsSiteService(db)
    site = await service.get_by_id(site_id)
    if not site or site.tenant_id != current_admin["tenant_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="站点不存在，请检查后重试")
    return _to_response(site)


@router.post("", response_model=SiteResponse, summary="创建站点")
async def create_site(
    data: SiteCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:site:create")),
):
    service = CmsSiteService(db)
    site = await service.create(
        data.model_dump(exclude_unset=True),
        tenant_id=current_admin["tenant_id"],
        operator_id=get_operator_id_from_admin(current_admin),
    )
    return _to_response(site)


@router.put("/{site_id}", response_model=SiteResponse, summary="更新站点")
async def update_site(
    site_id: str,
    data: SiteUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:site:update")),
):
    service = CmsSiteService(db)
    site = await service.update(
        site_id,
        data.model_dump(exclude_unset=True),
        operator_id=get_operator_id_from_admin(current_admin),
        tenant_id=current_admin["tenant_id"],
    )
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="站点不存在，请检查后重试")
    return _to_response(site)


@router.delete("/{site_id}", summary="删除站点（移入回收站）")
async def delete_site(
    site_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:site:delete")),
):
    service = CmsSiteService(db)
    success = await service.delete(site_id, tenant_id=current_admin["tenant_id"])
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="站点不存在，请检查后重试")
    return {"message": "删除成功"}


@router.post("/{site_id}/restore", summary="恢复站点")
async def restore_site(
    site_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:site:delete")),
):
    service = CmsSiteService(db)
    success = await service.restore(site_id, tenant_id=current_admin["tenant_id"])
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="站点不存在或未在回收站中")
    return {"message": "恢复成功"}


@router.delete("/{site_id}/permanent", summary="永久删除站点")
async def permanent_delete_site(
    site_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:site:delete")),
):
    service = CmsSiteService(db)
    success = await service.permanent_delete(site_id, tenant_id=current_admin["tenant_id"])
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="站点不存在，请检查后重试")
    return {"message": "永久删除成功"}


@router.post("/batch-delete", summary="批量删除站点")
async def batch_delete_sites(
    data: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:site:delete")),
):
    service = CmsSiteService(db)
    deleted_count = 0
    for site_id in data.ids:
        if await service.delete(site_id, tenant_id=current_admin["tenant_id"]):
            deleted_count += 1
    return {"message": f"成功删除 {deleted_count} 个站点", "deleted_count": deleted_count}
