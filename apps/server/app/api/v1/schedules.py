from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract
from typing import Optional, List
from datetime import date, datetime
from calendar import monthrange
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.schemas.schedule import ScheduleCreate, ScheduleBatchCreate, ScheduleUpdate, ScheduleResponse, AvailableScheduleResponse
from app.schemas.response import PageResponse
from app.services.schedule_service import ScheduleService
from app.services.notification_service import NotificationService
from app.models.schedule import Schedule
from app.models.custom_schedule import CustomSchedule
from app.models.doctor import Doctor
from app.models.store import Store

router = APIRouter()


class SuspendRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=200, description="停诊原因")
    notify_patients: bool = Field(True, description="是否通知患者")

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


class ScheduleStatisticsItem(BaseModel):
    """排班统计项"""
    schedule_date: date
    doctor_id: str
    doctor_name: str
    morning_slots: int = 0
    afternoon_slots: int = 0
    morning_booked: int = 0
    afternoon_booked: int = 0


class ScheduleStatisticsResponse(BaseModel):
    """排班统计响应"""
    store_id: str
    store_name: str
    year: int
    month: int
    items: List[ScheduleStatisticsItem]


@router.get("/statistics", response_model=ScheduleStatisticsResponse)
async def get_schedule_statistics(
    store_id: str = Query(..., description="门店ID"),
    year: int = Query(..., ge=2020, le=2100, description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    db: AsyncSession = Depends(get_db)
):
    """获取排班统计（按门店、月份）"""
    # 获取门店信息
    store_result = await db.execute(select(Store).where(Store.id == store_id))
    store = store_result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="门店不存在")
    
    # 计算月份的开始和结束日期
    start_date = date(year, month, 1)
    _, last_day = monthrange(year, month)
    end_date = date(year, month, last_day)
    
    # 获取门店下所有医生
    doctors_result = await db.execute(
        select(Doctor).where(Doctor.store_id == store_id, Doctor.status == 1)
    )
    doctors = doctors_result.scalars().all()
    doctor_map = {d.id: d.name for d in doctors}
    
    # 汇总统计数据
    stats_dict = {}  # key: (date, doctor_id)
    
    # 1. 获取普通排班统计
    normal_result = await db.execute(
        select(Schedule)
        .where(
            and_(
                Schedule.doctor_id.in_(list(doctor_map.keys())),
                Schedule.schedule_date >= start_date,
                Schedule.schedule_date <= end_date
            )
        )
    )
    normal_schedules = normal_result.scalars().all()
    
    for s in normal_schedules:
        key = (s.schedule_date, s.doctor_id)
        if key not in stats_dict:
            stats_dict[key] = {
                "morning_slots": 0,
                "afternoon_slots": 0,
                "morning_booked": 0,
                "afternoon_booked": 0
            }
        
        if s.time_slot in ["AM", "morning"]:
            stats_dict[key]["morning_slots"] += s.total_slots
            stats_dict[key]["morning_booked"] += s.booked_slots
        elif s.time_slot in ["PM", "afternoon"]:
            stats_dict[key]["afternoon_slots"] += s.total_slots
            stats_dict[key]["afternoon_booked"] += s.booked_slots
    
    # 2. 获取自定义排班统计
    custom_result = await db.execute(
        select(CustomSchedule)
        .where(
            and_(
                CustomSchedule.store_id == store_id,
                CustomSchedule.schedule_date >= start_date,
                CustomSchedule.schedule_date <= end_date,
                CustomSchedule.status == 1
            )
        )
    )
    custom_schedules = custom_result.scalars().all()
    
    for s in custom_schedules:
        key = (s.schedule_date, s.doctor_id)
        if key not in stats_dict:
            stats_dict[key] = {
                "morning_slots": 0,
                "afternoon_slots": 0,
                "morning_booked": 0,
                "afternoon_booked": 0
            }
        
        # 根据时间判断上午/下午
        if s.start_time.hour < 12:
            stats_dict[key]["morning_slots"] += s.max_patients
            stats_dict[key]["morning_booked"] += s.booked_count
        else:
            stats_dict[key]["afternoon_slots"] += s.max_patients
            stats_dict[key]["afternoon_booked"] += s.booked_count
    
    # 构建结果
    items = []
    for (schedule_date, doctor_id), stats in sorted(stats_dict.items()):
        items.append(ScheduleStatisticsItem(
            schedule_date=schedule_date,
            doctor_id=doctor_id,
            doctor_name=doctor_map.get(doctor_id, ""),
            morning_slots=stats["morning_slots"],
            afternoon_slots=stats["afternoon_slots"],
            morning_booked=stats["morning_booked"],
            afternoon_booked=stats["afternoon_booked"]
        ))
    
    return ScheduleStatisticsResponse(
        store_id=store_id,
        store_name=store.name,
        year=year,
        month=month,
        items=items
    )


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
async def suspend_schedule(
    schedule_id: str,
    data: SuspendRequest = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """停诊并通知患者"""
    service = ScheduleService(db)
    notification_service = NotificationService(db)
    
    # 先执行停诊
    schedule = await service.suspend(schedule_id)
    
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排班不存在")
    
    result = {"message": "停诊成功"}
    
    # 通知患者
    if data and data.notify_patients:
        notify_result = await notification_service.notify_suspend(
            schedule_id=schedule_id,
            reason=data.reason
        )
        result["notification"] = notify_result
    
    return result


@router.put("/{schedule_id}/resume")
async def resume_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """恢复排班"""
    service = ScheduleService(db)
    schedule = await service.resume(schedule_id)
    
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排班不存在")
    
    return {"message": "恢复成功"}
