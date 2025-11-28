"""患者管理 API（管理后台）"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.services.patient_service import PatientManageService
from app.schemas.response import PageResponse

router = APIRouter()


@router.get("")
async def get_patients(
    keyword: Optional[str] = None,
    is_blacklist: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取患者列表"""
    service = PatientManageService(db)
    items, total = await service.get_list(
        keyword=keyword,
        is_blacklist=is_blacklist,
        page=page,
        page_size=page_size,
    )
    return PageResponse(data=items, total=total, page=page, page_size=page_size)


@router.get("/blacklist")
async def get_blacklist(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取黑名单列表"""
    service = PatientManageService(db)
    items, total = await service.get_blacklist(page=page, page_size=page_size)
    return PageResponse(data=items, total=total, page=page, page_size=page_size)


@router.get("/{patient_id}")
async def get_patient_detail(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取患者详情"""
    service = PatientManageService(db)
    detail = await service.get_detail(patient_id)
    
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="患者不存在")
    
    return detail


@router.put("/{patient_id}/blacklist")
async def add_to_blacklist(
    patient_id: str,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """加入黑名单"""
    service = PatientManageService(db)
    success = await service.add_to_blacklist(patient_id, reason)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="患者不存在")
    
    return {"message": "已加入黑名单"}


@router.delete("/{patient_id}/blacklist")
async def remove_from_blacklist(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """移出黑名单"""
    service = PatientManageService(db)
    success = await service.remove_from_blacklist(patient_id)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="患者不存在")
    
    return {"message": "已移出黑名单"}


