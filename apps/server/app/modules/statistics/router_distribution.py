"""数据统计 - 时段与星期分布"""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_store_filter, get_tenant_filter
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.modules.statistics.helpers import (
    _build_store_filter_condition,
    _build_tenant_condition,
)
from app.schemas.response import ResponseModel

router = APIRouter()


@router.get("/time-slots/distribution", response_model=ResponseModel, summary="获取时段分布统计")
async def get_time_slot_distribution(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    tenant_id: str | None = Depends(get_tenant_filter),
):
    """获取时段分布统计"""
    # 获取门店过滤条件
    store_filter = get_store_filter(current_admin)
    store_condition = _build_store_filter_condition(store_filter)
    tenant_condition = _build_tenant_condition(Doctor, tenant_id)

    # 通过 Schedule 获取 time_slot
    query = (
        select(
            Schedule.time_slot,
            func.count(Appointment.id).label('count')
        )
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
    )

    if store_condition is not None:
        query = query.where(store_condition)
    if tenant_condition is not None:
        query = query.where(tenant_condition)

    query = query.group_by(Schedule.time_slot)
    result = await db.execute(query)

    slot_map = {
        "morning": "上午",
        "afternoon": "下午",
        "evening": "晚上",
    }

    data = [
        {"timeSlot": row.time_slot, "name": slot_map.get(row.time_slot, row.time_slot), "count": row.count}
        for row in result.fetchall()
    ]

    return ResponseModel(data=data)


@router.get("/weekday/distribution", response_model=ResponseModel, summary="获取星期分布统计")
async def get_weekday_distribution(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    tenant_id: str | None = Depends(get_tenant_filter),
):
    """获取星期分布统计"""
    # 获取门店过滤条件
    store_filter = get_store_filter(current_admin)
    store_condition = _build_store_filter_condition(store_filter)
    tenant_condition = _build_tenant_condition(Doctor, tenant_id)

    # 使用 extract 获取星期几（0=周日，1=周一...6=周六）- 通过 Schedule 获取 schedule_date
    query = (
        select(
            func.extract('dow', Schedule.schedule_date).label('weekday'),
            func.count(Appointment.id).label('count')
        )
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
    )

    if store_condition is not None:
        query = query.where(store_condition)
    if tenant_condition is not None:
        query = query.where(tenant_condition)

    query = query.group_by(
        func.extract('dow', Schedule.schedule_date)
    ).order_by(
        func.extract('dow', Schedule.schedule_date)
    )
    result = await db.execute(query)

    weekday_names = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]

    data = [
        {"weekday": int(row.weekday), "name": weekday_names[int(row.weekday)], "count": row.count}
        for row in result.fetchall()
    ]

    return ResponseModel(data=data)
