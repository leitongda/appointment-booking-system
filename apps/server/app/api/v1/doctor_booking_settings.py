from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.db.session import get_db
from app.schemas.doctor_booking_setting import (
    DoctorBookingSettingCreate,
    DoctorBookingSettingUpdate,
    DoctorBookingSettingResponse,
    DoctorBookingSettingQuery,
)
from app.schemas.response import PageResponse
from app.services.doctor_booking_setting_service import DoctorBookingSettingService
from app.core.config import settings

router = APIRouter()


@router.get("", response_model=PageResponse[DoctorBookingSettingResponse])
async def get_doctor_booking_settings(
    store_id: Optional[str] = None,
    doctor_id: Optional[str] = None,
    status: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db)
):
    """获取医生预约设置列表"""
    service = DoctorBookingSettingService(db)
    query = DoctorBookingSettingQuery(
        store_id=store_id,
        doctor_id=doctor_id,
        status=status,
        page=page,
        page_size=page_size
    )
    settings, total = await service.get_list(query)
    
    return PageResponse(
        data=[DoctorBookingSettingResponse(**s) for s in settings],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/existing-doctors", response_model=List[str])
async def get_existing_doctor_ids(
    store_id: str = Query(..., description="门店ID"),
    db: AsyncSession = Depends(get_db)
):
    """获取指定门店已配置的医生ID列表（用于前端禁用已配置的医生）"""
    service = DoctorBookingSettingService(db)
    return await service.get_existing_doctor_ids(store_id)


@router.get("/{setting_id}", response_model=DoctorBookingSettingResponse)
async def get_doctor_booking_setting(
    setting_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取医生预约设置详情"""
    service = DoctorBookingSettingService(db)
    setting = await service.get_by_id(setting_id)
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="设置不存在，请检查后重试"
        )
    
    return DoctorBookingSettingResponse.model_validate(setting)


@router.post("", response_model=DoctorBookingSettingResponse)
async def create_doctor_booking_setting(
    data: DoctorBookingSettingCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建医生预约设置"""
    service = DoctorBookingSettingService(db)
    
    try:
        setting = await service.create(data)
        # 需要重新查询以获取门店名和医生名
        settings, _ = await service.get_list(
            DoctorBookingSettingQuery(page=1, page_size=1)
        )
        # 找到刚创建的设置
        for s in settings:
            if s['id'] == setting.id:
                return DoctorBookingSettingResponse(**s)
        return DoctorBookingSettingResponse.model_validate(setting)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{setting_id}", response_model=DoctorBookingSettingResponse)
async def update_doctor_booking_setting(
    setting_id: str,
    data: DoctorBookingSettingUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新医生预约设置"""
    service = DoctorBookingSettingService(db)
    
    try:
        setting = await service.update(setting_id, data)
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="设置不存在，请检查后重试"
            )
        return DoctorBookingSettingResponse.model_validate(setting)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{setting_id}")
async def delete_doctor_booking_setting(
    setting_id: str,
    db: AsyncSession = Depends(get_db)
):
    """删除医生预约设置"""
    service = DoctorBookingSettingService(db)
    success = await service.delete(setting_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="设置不存在，请检查后重试"
        )
    
    return {"message": "删除成功"}


@router.patch("/{setting_id}/status")
async def update_doctor_booking_setting_status(
    setting_id: str,
    new_status: int = Query(..., ge=0, le=1, description="状态: 0禁用 1启用"),
    db: AsyncSession = Depends(get_db)
):
    """更新医生预约设置状态"""
    service = DoctorBookingSettingService(db)
    setting = await service.update_status(setting_id, new_status)
    
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="设置不存在，请检查后重试"
        )
    
    return {"message": "状态更新成功"}
