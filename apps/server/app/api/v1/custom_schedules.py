from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import date

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.schemas.custom_schedule import (
    CustomScheduleCreate,
    CustomScheduleResponse,
)
from app.schemas.response import PageResponse
from app.services.custom_schedule_service import CustomScheduleService

router = APIRouter()


@router.get("", response_model=PageResponse[CustomScheduleResponse])
async def get_custom_schedules(
    store_id: Optional[str] = None,
    department_id: Optional[str] = None,
    doctor_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    appointment_type: Optional[str] = None,
    status: Optional[int] = Query(None, ge=0, le=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取自定义排班列表"""
    service = CustomScheduleService(db)
    schedules, total = await service.get_list(
        store_id=store_id,
        department_id=department_id,
        doctor_id=doctor_id,
        start_date=start_date,
        end_date=end_date,
        appointment_type=appointment_type,
        status=status,
        page=page,
        page_size=page_size
    )
    
    result = []
    for s in schedules:
        result.append(CustomScheduleResponse(
            id=s.id,
            store_id=s.store_id,
            store_name=s.store.name if s.store else None,
            department_id=s.department_id,
            department_name=s.department.name if s.department else None,
            doctor_id=s.doctor_id,
            doctor_name=s.doctor.name if s.doctor else None,
            schedule_date=s.schedule_date,
            start_time=s.start_time,
            end_time=s.end_time,
            appointment_type=s.appointment_type,
            max_patients=s.max_patients,
            booked_count=s.booked_count,
            status=s.status,
            created_at=s.created_at
        ))
    
    return PageResponse(data=result, total=total, page=page, page_size=page_size)


@router.get("/effective", response_model=List[CustomScheduleResponse])
async def get_effective_schedules(
    store_id: Optional[str] = None,
    doctor_id: Optional[str] = None,
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """获取生效的自定义排班"""
    service = CustomScheduleService(db)
    schedules = await service.get_effective_schedules(
        store_id=store_id,
        doctor_id=doctor_id,
        start_date=start_date,
        end_date=end_date
    )
    
    result = []
    for s in schedules:
        result.append(CustomScheduleResponse(
            id=s.id,
            store_id=s.store_id,
            store_name=s.store.name if s.store else None,
            department_id=s.department_id,
            department_name=s.department.name if s.department else None,
            doctor_id=s.doctor_id,
            doctor_name=s.doctor.name if s.doctor else None,
            schedule_date=s.schedule_date,
            start_time=s.start_time,
            end_time=s.end_time,
            appointment_type=s.appointment_type,
            max_patients=s.max_patients,
            booked_count=s.booked_count,
            status=s.status,
            created_at=s.created_at
        ))
    
    return result


@router.post("", response_model=List[CustomScheduleResponse])
async def create_custom_schedules(
    data: CustomScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """创建自定义排班（支持批量）"""
    service = CustomScheduleService(db)
    
    try:
        schedules = await service.create(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    result = []
    for s in schedules:
        result.append(CustomScheduleResponse(
            id=s.id,
            store_id=s.store_id,
            store_name=None,
            department_id=s.department_id,
            department_name=None,
            doctor_id=s.doctor_id,
            doctor_name=None,
            schedule_date=s.schedule_date,
            start_time=s.start_time,
            end_time=s.end_time,
            appointment_type=s.appointment_type,
            max_patients=s.max_patients,
            booked_count=s.booked_count,
            status=s.status,
            created_at=s.created_at
        ))
    
    return result


@router.delete("/{schedule_id}")
async def delete_custom_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """删除自定义排班"""
    service = CustomScheduleService(db)
    
    try:
        success = await service.delete(schedule_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排班不存在")
    
    return {"message": "删除成功"}
