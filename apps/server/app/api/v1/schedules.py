from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import date

from app.db.session import get_db
from app.schemas.schedule import ScheduleCreate, ScheduleBatchCreate, ScheduleUpdate, ScheduleResponse, AvailableScheduleResponse
from app.schemas.response import PageResponse
from app.services.schedule_service import ScheduleService

router = APIRouter()

@router.get("", response_model=PageResponse[ScheduleResponse])
async def get_schedules(
    doctor_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取排班列表"""
    service = ScheduleService(db)
    schedules, total = await service.get_list(
        doctor_id=doctor_id, start_date=start_date, end_date=end_date,
        status=status, page=page, page_size=page_size
    )
    
    result = []
    for s in schedules:
        result.append(ScheduleResponse(
            id=s.id,
            doctor_id=s.doctor_id,
            doctor_name=s.doctor.name if s.doctor else None,
            department_name=s.doctor.department.name if s.doctor and s.doctor.department else None,
            schedule_date=s.schedule_date,
            time_slot=s.time_slot,
            start_time=s.start_time,
            end_time=s.end_time,
            total_slots=s.total_slots,
            booked_slots=s.booked_slots,
            status=s.status,
            created_at=s.created_at
        ))
    
    return PageResponse(data=result, total=total, page=page, page_size=page_size)

@router.get("/available/{doctor_id}", response_model=List[AvailableScheduleResponse])
async def get_available_schedules(
    doctor_id: str,
    days: int = Query(14, ge=1, le=30),
    db: AsyncSession = Depends(get_db)
):
    """获取可预约排班"""
    service = ScheduleService(db)
    schedules = await service.get_available(doctor_id, days=days)
    
    return [AvailableScheduleResponse(
        id=s.id,
        schedule_date=s.schedule_date,
        time_slot=s.time_slot,
        available_slots=s.total_slots - s.booked_slots,
        start_time=s.start_time,
        end_time=s.end_time
    ) for s in schedules]

@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(schedule_id: str, db: AsyncSession = Depends(get_db)):
    """获取排班详情"""
    service = ScheduleService(db)
    schedule = await service.get_by_id(schedule_id)
    
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排班不存在")
    
    return ScheduleResponse(
        id=schedule.id,
        doctor_id=schedule.doctor_id,
        doctor_name=schedule.doctor.name if schedule.doctor else None,
        department_name=schedule.doctor.department.name if schedule.doctor and schedule.doctor.department else None,
        schedule_date=schedule.schedule_date,
        time_slot=schedule.time_slot,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        total_slots=schedule.total_slots,
        booked_slots=schedule.booked_slots,
        status=schedule.status,
        created_at=schedule.created_at
    )

@router.post("", response_model=ScheduleResponse)
async def create_schedule(data: ScheduleCreate, db: AsyncSession = Depends(get_db)):
    """创建排班"""
    service = ScheduleService(db)
    
    try:
        schedule = await service.create(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return ScheduleResponse(
        id=schedule.id,
        doctor_id=schedule.doctor_id,
        schedule_date=schedule.schedule_date,
        time_slot=schedule.time_slot,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        total_slots=schedule.total_slots,
        booked_slots=schedule.booked_slots,
        status=schedule.status,
        created_at=schedule.created_at
    )

@router.post("/batch")
async def batch_create_schedules(data: ScheduleBatchCreate, db: AsyncSession = Depends(get_db)):
    """批量创建排班"""
    service = ScheduleService(db)
    created_count = await service.batch_create(data)
    return {"message": f"成功创建 {created_count} 条排班"}

@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: str,
    data: ScheduleUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新排班"""
    service = ScheduleService(db)
    
    try:
        schedule = await service.update(schedule_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排班不存在")
    
    return ScheduleResponse(
        id=schedule.id,
        doctor_id=schedule.doctor_id,
        schedule_date=schedule.schedule_date,
        time_slot=schedule.time_slot,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        total_slots=schedule.total_slots,
        booked_slots=schedule.booked_slots,
        status=schedule.status,
        created_at=schedule.created_at
    )

@router.put("/{schedule_id}/suspend")
async def suspend_schedule(schedule_id: str, db: AsyncSession = Depends(get_db)):
    """停诊"""
    service = ScheduleService(db)
    schedule = await service.suspend(schedule_id)
    
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排班不存在")
    
    return {"message": "停诊成功"}
