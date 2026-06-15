"""数据统计 - 预约趋势、状态与汇总"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_store_filter
from app.constants.appointment import APPOINTMENT_STATUS
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.modules.statistics.helpers import _build_store_filter_condition
from app.schemas.response import ResponseModel

router = APIRouter()


@router.get("/appointments/trend", response_model=ResponseModel, summary="获取预约趋势")
async def get_appointment_trend(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取预约趋势数据"""
    today = date.today()
    start_date = today - timedelta(days=days - 1)

    # 获取门店过滤条件
    store_filter = get_store_filter(current_admin)
    store_condition = _build_store_filter_condition(store_filter)

    # 查询每天的预约数（按门店过滤）
    query = (
        select(
            func.date(Appointment.created_at).label('date'),
            func.count(Appointment.id).label('count')
        )
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .where(func.date(Appointment.created_at) >= start_date)
    )
    if store_condition is not None:
        query = query.where(store_condition)

    query = query.group_by(func.date(Appointment.created_at)).order_by(func.date(Appointment.created_at))
    result = await db.execute(query)

    data = {str(row.date): row.count for row in result.fetchall()}

    # 填充缺失的日期
    trend = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        trend.append({
            "date": str(d),
            "count": data.get(str(d), 0)
        })

    return ResponseModel(data=trend)


@router.get("/appointments/status", response_model=ResponseModel, summary="获取预约状态统计")
async def get_appointment_status_stats(
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取预约状态统计"""
    # 获取门店过滤条件
    store_filter = get_store_filter(current_admin)
    store_condition = _build_store_filter_condition(store_filter)

    query = (
        select(
            Appointment.status,
            func.count(Appointment.id).label('count')
        )
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
    )

    conditions = []
    if start_date:
        conditions.append(func.date(Appointment.created_at) >= start_date)
    if end_date:
        conditions.append(func.date(Appointment.created_at) <= end_date)
    if store_condition is not None:
        conditions.append(store_condition)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.group_by(Appointment.status)

    result = await db.execute(query)

    status_map = {
        0: "待支付",
        1: "已预约",
        2: "已签到",
        3: "历史候诊",
        4: "就诊中",
        5: "已完成",
        6: "已取消",
        7: "已过期",
        8: "已爽约",
    }

    data = [
        {"status": row.status, "name": status_map.get(row.status, "未知"), "count": row.count}
        for row in result.fetchall()
    ]

    return ResponseModel(data=data)


@router.get("/appointments/summary", response_model=ResponseModel, summary="获取预约汇总统计")
async def get_appointment_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    store_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取预约汇总统计（完成率/爽约率/取消率）"""
    # 获取门店过滤条件
    store_filter = get_store_filter(current_admin)

    query = (
        select(
            func.count(Appointment.id).label('total'),
            func.sum(case((Appointment.status == APPOINTMENT_STATUS["COMPLETED"], 1), else_=0)).label('completed'),
            func.sum(case((Appointment.status == APPOINTMENT_STATUS["NO_SHOW"], 1), else_=0)).label('no_show'),
            func.sum(case((Appointment.status == APPOINTMENT_STATUS["CANCELLED"], 1), else_=0)).label('cancelled'),
        )
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
    )

    conditions = []

    if start_date:
        conditions.append(func.date(Appointment.created_at) >= start_date)
    if end_date:
        conditions.append(func.date(Appointment.created_at) <= end_date)

    # 优先使用管理员的门店过滤，如果是超管则可以使用传入的 store_id
    if store_filter is not None:
        store_condition = _build_store_filter_condition(store_filter)
        if store_condition is not None:
            conditions.append(store_condition)
    elif store_id:
        conditions.append(Doctor.store_id == store_id)

    if conditions:
        query = query.where(and_(*conditions))

    result = await db.execute(query)
    row = result.fetchone()

    total = row.total or 0
    completed = row.completed or 0
    no_show = row.no_show or 0
    cancelled = row.cancelled or 0

    return ResponseModel(data={
        "total": total,
        "completed": completed,
        "noShow": no_show,
        "cancelled": cancelled,
        "completedRate": round(completed / total * 100, 2) if total > 0 else 0,
        "noShowRate": round(no_show / total * 100, 2) if total > 0 else 0,
        "cancelledRate": round(cancelled / total * 100, 2) if total > 0 else 0,
    })
