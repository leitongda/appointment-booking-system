"""排班管理相关端点"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, timedelta
from typing import Optional, List

from app.db.session import get_db
from app.api.deps import get_current_doctor_by_token
from app.models.doctor import Doctor
from app.models.rest_day import RestDay
from app.modules.schedules.service import ScheduleService
from app.modules.doctor_portal.schemas import DoctorScheduleResponse

router = APIRouter()


def _check_rest_day_for_schedule(
    schedule_date: date,
    store_id: Optional[str],
    doctor_id: str,
    rest_days: List
) -> bool:
    """检查指定排班是否在休息日"""
    for rd in rest_days:
        # 检查日期是否在休息日范围内
        if not (rd.start_date <= schedule_date <= rd.end_date):
            continue
        # 检查门店是否匹配
        if store_id and rd.store_id != store_id:
            continue
        # 如果 doctor_ids 为空，表示门店所有医生休息
        if rd.doctor_ids is None:
            return True
        # 检查医生是否在休息日列表中
        try:
            doctor_ids_list = rd.doctor_ids
            if isinstance(doctor_ids_list, str):
                doctor_ids_list = doctor_ids_list.split(",")
            if doctor_id in doctor_ids_list:
                return True
        except Exception:
            pass
    return False


@router.get("", response_model=List[DoctorScheduleResponse], summary="获取排班列表")
async def get_my_schedules(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[int] = None,
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """获取当前医生的排班列表

    自动限制为当前医生的排班，    """
    service = ScheduleService(db)

    # 默认查询未来7天的排班
    if not start_date:
        start_date = date.today()
    if not end_date:
        end_date = start_date + timedelta(days=7)

    schedules, _ = await service.get_list(
        doctor_id=doctor.id,
        store_id=doctor.store_id,  # 门店隔离
        start_date=start_date,
        end_date=end_date,
        status=status,
        page=1,
        page_size=100  # 医生端一般不需要分页
    )

    # 查询日期范围内的所有有效休息日
    rest_days = []
    if schedules:
        rest_day_result = await db.execute(
            select(RestDay).where(
                RestDay.status == 1,
                RestDay.start_date <= end_date,
                RestDay.end_date >= start_date,
                RestDay.store_id == doctor.store_id
            )
        )
        rest_days = rest_day_result.scalars().all()

    return [
        DoctorScheduleResponse(
            id=s.id,
            doctor_id=doctor.id,
            store_id=doctor.store_id,
            schedule_date=s.schedule_date,
            time_slot=s.time_slot,
            start_time=s.start_time,
            end_time=s.end_time,
            total_slots=s.total_slots,
            booked_slots=s.booked_slots,
            status=s.status,
            is_rest_day=_check_rest_day_for_schedule(
                s.schedule_date, s.store_id, doctor.id, rest_days
            ),
        )
        for s in schedules
    ]


@router.get("/today", response_model=List[DoctorScheduleResponse], summary="获取今日排班")
async def get_my_today_schedules(
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """获取当前医生今日排班"""
    today = date.today()
    service = ScheduleService(db)

    schedules, _ = await service.get_list(
        doctor_id=doctor.id,
        store_id=doctor.store_id,
        start_date=today,
        end_date=today,
        page=1,
        page_size=10
    )

    # 查询今日的休息日
    rest_days = []
    if schedules:
        rest_day_result = await db.execute(
            select(RestDay).where(
                RestDay.status == 1,
                RestDay.start_date <= today,
                RestDay.end_date >= today,
                RestDay.store_id == doctor.store_id
            )
        )
        rest_days = rest_day_result.scalars().all()

    return [
        DoctorScheduleResponse(
            id=s.id,
            doctor_id=doctor.id,
            store_id=doctor.store_id,
            schedule_date=s.schedule_date,
            time_slot=s.time_slot,
            start_time=s.start_time,
            end_time=s.end_time,
            total_slots=s.total_slots,
            booked_slots=s.booked_slots,
            status=s.status,
            is_rest_day=_check_rest_day_for_schedule(
                s.schedule_date, s.store_id, doctor.id, rest_days
            ),
        )
        for s in schedules
    ]
