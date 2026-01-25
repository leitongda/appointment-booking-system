"""预约须知 API"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.services.booking_notice_service import BookingNoticeService
from app.schemas.booking_notice import (
    BookingNoticeCreate,
    BookingNoticeUpdate,
    BookingNoticeResponse,
)
from app.core.config import settings

router = APIRouter()


# ========== 公开接口 ==========

@router.get("/public", response_model=List[BookingNoticeResponse])
async def get_public_notices(
    type: Optional[str] = Query(None, description="类型: BOOKING/VISIT/REFUND"),
    db: AsyncSession = Depends(get_db)
):
    """获取生效的预约须知列表（公开接口，供小程序端调用）"""
    service = BookingNoticeService(db)
    notices = await service.get_active_list(notice_type=type)
    return notices


# ========== 管理端接口 ==========

@router.get("", response_model=dict)
async def get_notices(
    type: Optional[str] = Query(None, description="类型"),
    status: Optional[int] = Query(None, description="状态: 0禁用 1启用"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=settings.MAX_PAGE_SIZE, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取预约须知列表（管理端）"""
    service = BookingNoticeService(db)
    notices, total = await service.get_list(
        notice_type=type,
        status=status,
        page=page,
        page_size=page_size
    )
    
    return {
        "data": [BookingNoticeResponse.model_validate(n) for n in notices],
        "total": total,
        "page": page,
        "pageSize": page_size
    }


@router.get("/{notice_id}", response_model=BookingNoticeResponse)
async def get_notice(
    notice_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取预约须知详情"""
    service = BookingNoticeService(db)
    notice = await service.get_by_id(notice_id)
    
    if not notice:
        raise HTTPException(status_code=404, detail="预约须知不存在")
    
    return notice


@router.post("", response_model=BookingNoticeResponse, status_code=status.HTTP_201_CREATED)
async def create_notice(
    data: BookingNoticeCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """创建预约须知"""
    service = BookingNoticeService(db)
    notice = await service.create(data, operator_id=current_admin.get("id"))
    return notice


@router.put("/{notice_id}", response_model=BookingNoticeResponse)
async def update_notice(
    notice_id: str,
    data: BookingNoticeUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """更新预约须知"""
    service = BookingNoticeService(db)
    notice = await service.update(notice_id, data, operator_id=current_admin.get("id"))
    
    if not notice:
        raise HTTPException(status_code=404, detail="预约须知不存在")
    
    return notice


@router.delete("/{notice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notice(
    notice_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """删除预约须知"""
    service = BookingNoticeService(db)
    success = await service.delete(notice_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="预约须知不存在")


@router.patch("/{notice_id}/status", response_model=BookingNoticeResponse)
async def update_notice_status(
    notice_id: str,
    status: int = Query(..., ge=0, le=1, description="状态: 0禁用 1启用"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """更新预约须知状态"""
    service = BookingNoticeService(db)
    notice = await service.update_status(notice_id, status, operator_id=current_admin.get("id"))
    
    if not notice:
        raise HTTPException(status_code=404, detail="预约须知不存在")
    
    return notice

