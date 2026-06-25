"""操作指引 - 用户端路由

前缀 /guide-tours。所有已登录用户可访问。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth_unified import require_role
from app.common.auth_types import AccountInfo, RoleType
from app.db.session import get_db
from app.modules.guide_tours.schemas import ProgressUpdate
from app.modules.guide_tours.service import GuideTourService
from app.schemas.response import ResponseModel

router = APIRouter()


@router.get("/active", response_model=ResponseModel, summary="获取已发布指引列表")
async def get_active_tours(
    db: AsyncSession = Depends(get_db),
    current_admin: AccountInfo = Depends(require_role(RoleType.ADMIN)),
):
    """获取当前用户可见的已发布指引，含用户进度。"""
    service = GuideTourService(db)
    items = await service.get_active_tours(admin_id=current_admin.id)
    return ResponseModel(data=items)


@router.get("/{tour_id}/progress", response_model=ResponseModel, summary="获取指引进度")
async def get_progress(
    tour_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: AccountInfo = Depends(require_role(RoleType.ADMIN)),
):
    """获取指定指引的当前用户进度。"""
    service = GuideTourService(db)
    progress = await service.get_progress(tour_id=tour_id, admin_id=current_admin.id)
    if progress is None:
        return ResponseModel(data={"currentStep": 0, "status": 0})
    return ResponseModel(data={
        "currentStep": progress.current_step,
        "status": progress.status,
    })


@router.post("/{tour_id}/progress", response_model=ResponseModel, summary="更新指引进度")
async def update_progress(
    tour_id: str,
    data: ProgressUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: AccountInfo = Depends(require_role(RoleType.ADMIN)),
):
    """更新当前用户的指引进度（步骤或状态）。"""
    service = GuideTourService(db)
    progress = await service.update_progress(
        tour_id=tour_id, admin_id=current_admin.id, data=data
    )
    return ResponseModel(data={
        "currentStep": progress.current_step,
        "status": progress.status,
    })
