"""操作指引 - 管理端路由

前缀 /admin/guide-tours。仅平台管理员可访问。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import require_platform_admin
from app.db.session import get_db
from app.modules.guide_tours.schemas import (
    GuideTourCreate,
    GuideTourUpdate,
    StatusUpdate,
)
from app.modules.guide_tours.service import AdminGuideTourService
from app.schemas.response import ResponseModel

router = APIRouter()


@router.get("", response_model=ResponseModel, summary="指引列表")
async def get_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    status: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin()),
):
    """分页获取指引列表。"""
    service = AdminGuideTourService(db)
    items, total = await service.get_list(page=page, page_size=page_size, status=status)
    return ResponseModel(data={"data": items, "total": total, "page": page, "pageSize": page_size})


@router.post("", response_model=ResponseModel, summary="创建指引")
async def create(
    data: GuideTourCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin()),
):
    """创建操作指引。"""
    service = AdminGuideTourService(db)
    tour = await service.create(data=data, created_by=current_admin["id"])
    return ResponseModel(data={"id": tour.id})


@router.put("/{tour_id}", response_model=ResponseModel, summary="更新指引")
async def update(
    tour_id: str,
    data: GuideTourUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin()),
):
    """更新操作指引。"""
    service = AdminGuideTourService(db)
    tour = await service.update(tour_id=tour_id, data=data, updated_by=current_admin["id"])
    if tour is None:
        return ResponseModel(code=404, message="指引不存在")
    return ResponseModel(data={"id": tour.id})


@router.patch("/{tour_id}/status", response_model=ResponseModel, summary="更新发布状态")
async def update_status(
    tour_id: str,
    data: StatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin()),
):
    """发布或下线指引。"""
    service = AdminGuideTourService(db)
    tour = await service.update_status(tour_id=tour_id, status=data.status, updated_by=current_admin["id"])
    if tour is None:
        return ResponseModel(code=404, message="指引不存在")
    return ResponseModel(data={"id": tour.id, "status": tour.status})


@router.delete("/{tour_id}", response_model=ResponseModel, summary="删除指引")
async def delete(
    tour_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin()),
):
    """删除操作指引。"""
    service = AdminGuideTourService(db)
    deleted = await service.delete(tour_id=tour_id)
    if not deleted:
        return ResponseModel(code=404, message="指引不存在")
    return ResponseModel(message="删除成功")
