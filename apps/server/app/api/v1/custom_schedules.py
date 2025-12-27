from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import date

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.schemas.custom_schedule import (
    CustomScheduleCreate,
    CustomScheduleResponse,
)
from app.schemas.response import PageResponse
from app.services.schedule_service import ScheduleService
from app.models.schedule import Schedule
from app.utils.schedule_utils import get_time_slot_from_time

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
    """获取自定义排班列表（template_id为NULL的排班）"""
    from app.models.doctor import Doctor
    
    query = select(Schedule).options(
        selectinload(Schedule.doctor).selectinload(Doctor.department),
        selectinload(Schedule.store)
    ).where(Schedule.template_id.is_(None))
    count_query = select(func.count(Schedule.id)).where(Schedule.template_id.is_(None))
    
    conditions = []
    if store_id:
        conditions.append(Schedule.store_id == store_id)
    if doctor_id:
        conditions.append(Schedule.doctor_id == doctor_id)
    if start_date:
        conditions.append(Schedule.schedule_date >= start_date)
    if end_date:
        conditions.append(Schedule.schedule_date <= end_date)
    if appointment_type:
        conditions.append(Schedule.appointment_type == appointment_type)
    if status is not None:
        conditions.append(Schedule.status == status)
    
    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))
    
    # 如果指定了department_id，需要通过doctor关联查询
    if department_id:
        query = query.join(Doctor).where(Doctor.department_id == department_id)
        count_query = count_query.join(Doctor).where(Doctor.department_id == department_id)
    
    query = query.order_by(Schedule.schedule_date, Schedule.start_time)
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result_query = await db.execute(query)
    schedules = result_query.scalars().all()
    
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    result = []
    for s in schedules:
        result.append(CustomScheduleResponse(
            id=s.id,
            store_id=s.store_id,
            store_name=s.store.name if s.store else None,
            department_id=s.doctor.department_id if s.doctor and s.doctor.department else None,
            department_name=s.doctor.department.name if s.doctor and s.doctor.department else None,
            doctor_id=s.doctor_id,
            doctor_name=s.doctor.name if s.doctor else None,
            schedule_date=s.schedule_date,
            start_time=s.start_time,
            end_time=s.end_time,
            appointment_type=s.appointment_type,
            max_patients=s.total_slots,
            booked_count=s.booked_slots,
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
    """获取生效的自定义排班（template_id为NULL的排班）"""
    from app.models.doctor import Doctor
    
    query = select(Schedule).options(
        selectinload(Schedule.doctor).selectinload(Doctor.department),
        selectinload(Schedule.store)
    ).where(
        and_(
            Schedule.template_id.is_(None),
            Schedule.status == 1,
            Schedule.schedule_date >= start_date,
            Schedule.schedule_date <= end_date
        )
    )
    
    if store_id:
        query = query.where(Schedule.store_id == store_id)
    if doctor_id:
        query = query.where(Schedule.doctor_id == doctor_id)
    
    query = query.order_by(Schedule.schedule_date, Schedule.start_time)
    
    result_query = await db.execute(query)
    schedules = result_query.scalars().all()
    
    result = []
    for s in schedules:
        result.append(CustomScheduleResponse(
            id=s.id,
            store_id=s.store_id,
            store_name=s.store.name if s.store else None,
            department_id=s.doctor.department_id if s.doctor and s.doctor.department else None,
            department_name=s.doctor.department.name if s.doctor and s.doctor.department else None,
            doctor_id=s.doctor_id,
            doctor_name=s.doctor.name if s.doctor else None,
            schedule_date=s.schedule_date,
            start_time=s.start_time,
            end_time=s.end_time,
            appointment_type=s.appointment_type,
            max_patients=s.total_slots,
            booked_count=s.booked_slots,
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
    from app.schemas.schedule import ScheduleCreate
    from app.utils.schedule_utils import split_time_range
    
    service = ScheduleService(db)
    created_schedules = []
    
    try:
        for schedule_date in data.schedule_dates:
            for period in data.time_periods:
                # 判断是否需要均分时段
                if period.slot_count and period.slot_count > 1:
                    # 自动均分时段
                    time_slots = split_time_range(
                        period.start_time, 
                        period.end_time, 
                        period.slot_count
                    )
                    for slot_start, slot_end in time_slots:
                        time_slot = get_time_slot_from_time(slot_start)
                        schedule_data = ScheduleCreate(
                            doctor_id=data.doctor_id,
                            store_id=data.store_id,
                            schedule_date=schedule_date,
                            time_slot=time_slot,
                            start_time=slot_start,
                            end_time=slot_end,
                            total_slots=period.max_patients,
                            appointment_type=period.appointment_type.value,
                            status=1,
                            template_id=None  # 自定义排班没有模板ID
                        )
                        schedule = await service.create(schedule_data)
                        created_schedules.append(schedule)
                else:
                    # 不均分，直接使用指定的时间段
                    time_slot = get_time_slot_from_time(period.start_time)
                    schedule_data = ScheduleCreate(
                        doctor_id=data.doctor_id,
                        store_id=data.store_id,
                        schedule_date=schedule_date,
                        time_slot=time_slot,
                        start_time=period.start_time,
                        end_time=period.end_time,
                        total_slots=period.max_patients,
                        appointment_type=period.appointment_type.value,
                        status=1,
                        template_id=None  # 自定义排班没有模板ID
                    )
                    schedule = await service.create(schedule_data)
                    created_schedules.append(schedule)
        
        # 重新加载关联数据
        result = []
        for s in created_schedules:
            await db.refresh(s)
            # 重新加载关联数据
            await db.refresh(s, ["doctor", "store"])
            if s.doctor:
                await db.refresh(s.doctor, ["department"])
            result.append(CustomScheduleResponse(
                id=s.id,
                store_id=s.store_id,
                store_name=s.store.name if s.store else None,
                department_id=s.doctor.department_id if s.doctor and s.doctor.department else None,
                department_name=s.doctor.department.name if s.doctor and s.doctor.department else None,
                doctor_id=s.doctor_id,
                doctor_name=s.doctor.name if s.doctor else None,
                schedule_date=s.schedule_date,
                start_time=s.start_time,
                end_time=s.end_time,
                appointment_type=s.appointment_type,
                max_patients=s.total_slots,
                booked_count=s.booked_slots,
                status=s.status,
                created_at=s.created_at
            ))
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{schedule_id}")
async def delete_custom_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """删除自定义排班（仅能删除template_id为NULL的排班）"""
    service = ScheduleService(db)
    
    schedule = await service.get_by_id(schedule_id)
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排班不存在")
    
    if schedule.template_id is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只能删除自定义排班")
    
    if schedule.booked_slots > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该排班已有预约，无法删除")
    
    await db.delete(schedule)
    await db.commit()
    
    return {"message": "删除成功"}
