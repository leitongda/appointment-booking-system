"""Booking notices domain router."""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.modules.booking_notices.service import BookingNoticeService
from app.schemas.booking_notice import (
    BookingNoticeCreate,
    BookingNoticeResponse,
    BookingNoticeUpdate,
)

router = APIRouter()


@router.get("/public", response_model=list[BookingNoticeResponse], summary="获取生效预约须知列表")
async def get_public_notices(
    type: str | None = Query(None, description="类型: BOOKING/VISIT/REFUND"),
    db: AsyncSession = Depends(get_db),
):
    service = BookingNoticeService(db)
    return await service.get_active_list(notice_type=type)


@router.get("", response_model=dict, summary="获取预约须知列表")
async def get_notices(
    type: str | None = Query(None, description="类型"),
    status: int | None = Query(None, description="状态: 0禁用 1启用"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=settings.MAX_PAGE_SIZE, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    service = BookingNoticeService(db)
    notices, total = await service.get_list(
        notice_type=type,
        status=status,
        page=page,
        page_size=page_size,
    )
    return {
        "data": [BookingNoticeResponse.model_validate(n) for n in notices],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.get("/{notice_id}", response_model=BookingNoticeResponse, summary="获取预约须知详情")
async def get_notice(
    notice_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    service = BookingNoticeService(db)
    notice = await service.get_by_id(notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="预约须知不存在")
    return notice


@router.post("", response_model=BookingNoticeResponse, status_code=status.HTTP_201_CREATED, summary="创建预约须知")
async def create_notice(
    data: BookingNoticeCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:notice:create")),
):
    service = BookingNoticeService(db)
    return await service.create(data, operator_id=current_admin.get("id"))


@router.put("/{notice_id}", response_model=BookingNoticeResponse, summary="更新预约须知")
async def update_notice(
    notice_id: str,
    data: BookingNoticeUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:notice:update")),
):
    service = BookingNoticeService(db)
    notice = await service.update(notice_id, data, operator_id=current_admin.get("id"))
    if not notice:
        raise HTTPException(status_code=404, detail="预约须知不存在")
    return notice


@router.delete("/{notice_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除预约须知")
async def delete_notice(
    notice_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:notice:delete")),
):
    service = BookingNoticeService(db)
    success = await service.delete(notice_id)
    if not success:
        raise HTTPException(status_code=404, detail="预约须知不存在")


@router.patch("/{notice_id}/status", response_model=BookingNoticeResponse, summary="更新预约须知状态")
async def update_notice_status(
    notice_id: str,
    new_status: int = Query(..., ge=0, le=1, description="状态: 0禁用 1启用", alias="status"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:notice:update")),
):
    service = BookingNoticeService(db)
    notice = await service.update_status(notice_id, new_status, operator_id=current_admin.get("id"))
    if not notice:
        raise HTTPException(status_code=404, detail="预约须知不存在")
    return notice
