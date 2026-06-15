from calendar import monthrange
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_store_access, get_current_admin, get_store_filter, require_permission
from app.db.session import get_db
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.store import Store
from app.schemas.schedule import (
    DoctorWorkloadResponse,
    PeakHourHeatmapResponse,
    UtilizationTrendResponse,
)

router = APIRouter()


class ScheduleStatisticsItem(BaseModel):
    """排班统计项"""
    schedule_date: date
    doctor_id: str
    doctor_name: str
    morning_slots: int = 0
    afternoon_slots: int = 0
    evening_slots: int = 0
    morning_booked: int = 0
    afternoon_booked: int = 0
    evening_booked: int = 0


class ScheduleStatisticsResponse(BaseModel):
    """排班统计响应"""
    store_id: str
    store_name: str
    year: int
    month: int
    items: list[ScheduleStatisticsItem]


@router.get(
    "/statistics",
    response_model=ScheduleStatisticsResponse,
    summary="获取排班统计",
    description="""
    获取指定门店某月的排班统计数据，按医生和日期汇总。

    **参数说明**：
    - store_id: 门店ID（门店管理员自动取本门店，超级管理员必填）
    - year: 年份（必填，2020-2100）
    - month: 月份（必填，1-12）

    **返回数据**：
    - 按日期 + 医生维度汇总
    - 分别统计上午（morning）、下午（afternoon）、晚间（evening）的号源总量和已预约量
    - 同时包含自定义排班（非模板生成）的统计
    """,
)
async def get_schedule_statistics(
    store_id: str | None = Query(None, description="门店ID"),
    year: int = Query(..., ge=2020, le=2100, description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:read"))
):
    """获取排班统计（按门店、月份）"""
    # 门店过滤
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter
    elif not store_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择门店")

    # 检查门店访问权限
    if not check_store_access(current_admin, store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权访问此门店数据")

    # 获取门店信息
    store_result = await db.execute(select(Store).where(Store.id == store_id))
    store = store_result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="门店不存在，请检查后重试")

    # 计算月份的开始和结束日期
    start_date = date(year, month, 1)
    _, last_day = monthrange(year, month)
    end_date = date(year, month, last_day)

    # 获取门店下所有医生
    doctors_result = await db.execute(
        select(Doctor).where(Doctor.store_id == store_id, Doctor.status == 1, Doctor.deleted_at.is_(None))
    )
    doctors = doctors_result.scalars().all()
    doctor_map = {d.id: d.name for d in doctors}

    # 汇总统计数据
    stats_dict = {}  # key: (date, doctor_id)

    # 1. 获取普通排班统计（添加 store_id 过滤，确保门店隔离）
    normal_result = await db.execute(
        select(Schedule)
        .where(
            and_(
                Schedule.store_id == store_id,
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
                "evening_slots": 0,
                "morning_booked": 0,
                "afternoon_booked": 0,
                "evening_booked": 0
            }

        if s.time_slot == "morning":
            stats_dict[key]["morning_slots"] += s.total_slots
            stats_dict[key]["morning_booked"] += s.booked_slots
        elif s.time_slot == "afternoon":
            stats_dict[key]["afternoon_slots"] += s.total_slots
            stats_dict[key]["afternoon_booked"] += s.booked_slots
        elif s.time_slot == "evening":
            stats_dict[key]["evening_slots"] += s.total_slots
            stats_dict[key]["evening_booked"] += s.booked_slots

    # 2. 获取自定义排班统计（template_id为NULL的排班，添加 doctor_id 过滤确保门店隔离）
    custom_result = await db.execute(
        select(Schedule)
        .where(
            and_(
                Schedule.store_id == store_id,
                Schedule.doctor_id.in_(list(doctor_map.keys())),  # 只查询该门店下的医生
                Schedule.schedule_date >= start_date,
                Schedule.schedule_date <= end_date,
                Schedule.status == 1,
                Schedule.template_id.is_(None)  # 自定义排班
            )
        )
    )
    custom_schedule_list = custom_result.scalars().all()

    for s in custom_schedule_list:
        key = (s.schedule_date, s.doctor_id)
        if key not in stats_dict:
            stats_dict[key] = {
                "morning_slots": 0,
                "afternoon_slots": 0,
                "evening_slots": 0,
                "morning_booked": 0,
                "afternoon_booked": 0,
                "evening_booked": 0
            }

        # 根据时间判断上午/下午/晚间
        if s.start_time and s.start_time.hour < 12:
            stats_dict[key]["morning_slots"] += s.total_slots
            stats_dict[key]["morning_booked"] += s.booked_slots
        elif s.start_time and s.start_time.hour >= 18:
            stats_dict[key]["evening_slots"] += s.total_slots
            stats_dict[key]["evening_booked"] += s.booked_slots
        elif s.start_time:
            stats_dict[key]["afternoon_slots"] += s.total_slots
            stats_dict[key]["afternoon_booked"] += s.booked_slots

    # 构建结果
    items = []
    for (schedule_date, doctor_id), stats in sorted(stats_dict.items()):
        items.append(ScheduleStatisticsItem(
            schedule_date=schedule_date,
            doctor_id=doctor_id,
            doctor_name=doctor_map.get(doctor_id, ""),
            morning_slots=stats["morning_slots"],
            afternoon_slots=stats["afternoon_slots"],
            evening_slots=stats["evening_slots"],
            morning_booked=stats["morning_booked"],
            afternoon_booked=stats["afternoon_booked"],
            evening_booked=stats["evening_booked"]
        ))

    return ScheduleStatisticsResponse(
        store_id=store_id,
        store_name=store.name,
        year=year,
        month=month,
        items=items
    )


# ========== 排班统计增强端点 ==========


@router.get(
    "/statistics/utilization-trend",
    response_model=UtilizationTrendResponse,
    summary="排班利用率趋势",
    description="""
    获取指定门店在某日期范围内的排班利用率趋势。

    **参数说明**：
    - store_id: 门店ID（门店管理员自动取本门店，超级管理员必填）
    - start_date: 开始日期（必填）
    - end_date: 结束日期（必填）
    - granularity: 粒度，week（周）或 month（月），默认 week

    **返回数据**：
    - 按周或按月汇总的总号源、已预约号源、利用率
    """,
)
async def get_utilization_trend(
    store_id: str | None = Query(None, description="门店ID"),
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    granularity: str = Query("week", pattern="^(week|month)$", description="粒度: week / month"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:read"))
):
    """排班利用率趋势"""
    # 门店过滤
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter
    elif not store_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择门店")

    # 检查门店访问权限
    if not check_store_access(current_admin, store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权访问此门店数据")

    # 获取门店信息
    store_result = await db.execute(select(Store).where(Store.id == store_id))
    store = store_result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="门店不存在")

    # 查询该日期范围内的所有排班（status=1 且 template_id 不为 NULL，排除自定义排班重复统计）
    result = await db.execute(
        select(Schedule)
        .where(
            and_(
                Schedule.store_id == store_id,
                Schedule.schedule_date >= start_date,
                Schedule.schedule_date <= end_date,
                Schedule.status == 1,
            )
        )
    )
    schedules = result.scalars().all()

    period_stats = defaultdict(lambda: {"total_slots": 0, "booked_slots": 0})

    for s in schedules:
        if granularity == "month":
            period_key = s.schedule_date.strftime("%Y-%m")
        else:
            # ISO week: YYYY-WNN
            year_num, week_num, _ = s.schedule_date.isocalendar()
            period_key = f"{year_num}-W{week_num:02d}"
        period_stats[period_key]["total_slots"] += s.total_slots
        period_stats[period_key]["booked_slots"] += s.booked_slots

    items = []
    for period in sorted(period_stats.keys()):
        stats = period_stats[period]
        total = stats["total_slots"]
        booked = stats["booked_slots"]
        rate = round(booked / total * 100, 1) if total > 0 else 0.0
        items.append({
            "period": period,
            "total_slots": total,
            "booked_slots": booked,
            "utilization_rate": rate,
        })

    return UtilizationTrendResponse(
        store_id=store_id,
        store_name=store.name,
        granularity=granularity,
        items=items
    )


@router.get(
    "/statistics/doctor-workload",
    response_model=DoctorWorkloadResponse,
    summary="医生工作量对比",
    description="""
    获取指定门店在某日期范围内各医生的工作量对比数据。

    **参数说明**：
    - store_id: 门店ID（门店管理员自动取本门店，超级管理员必填）
    - start_date: 开始日期（必填）
    - end_date: 结束日期（必填）

    **返回数据**：
    - 每位医生的总号源、已预约、已完成预约、利用率、排班天数
    """,
)
async def get_doctor_workload(
    store_id: str | None = Query(None, description="门店ID"),
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:read"))
):
    """医生工作量对比"""
    # 门店过滤
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter
    elif not store_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择门店")

    if not check_store_access(current_admin, store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权访问此门店数据")

    store_result = await db.execute(select(Store).where(Store.id == store_id))
    store = store_result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="门店不存在")

    # 获取门店下所有医生
    doctors_result = await db.execute(
        select(Doctor).where(Doctor.store_id == store_id, Doctor.status == 1, Doctor.deleted_at.is_(None))
    )
    doctors = doctors_result.scalars().all()
    doctor_map = {d.id: d for d in doctors}

    # 查询排班数据
    schedule_result = await db.execute(
        select(Schedule).where(
            and_(
                Schedule.store_id == store_id,
                Schedule.schedule_date >= start_date,
                Schedule.schedule_date <= end_date,
                Schedule.status == 1,
            )
        )
    )
    schedules = schedule_result.scalars().all()

    # 查询已完成预约数量（status=5 已完成），通过 schedule 关联过滤门店和日期
    from app.models.appointment import Appointment
    appointment_result = await db.execute(
        select(Appointment.doctor_id, func.count(Appointment.id))
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .where(
            and_(
                Schedule.store_id == store_id,
                Schedule.schedule_date >= start_date,
                Schedule.schedule_date <= end_date,
                Appointment.status == 5,
            )
        )
        .group_by(Appointment.doctor_id)
    )
    completed_map = {row[0]: row[1] for row in appointment_result.all()}

    doc_stats = defaultdict(lambda: {
        "total_slots": 0,
        "booked_slots": 0,
        "schedule_days": set(),
    })

    for s in schedules:
        if s.doctor_id not in doctor_map:
            continue
        doc_stats[s.doctor_id]["total_slots"] += s.total_slots
        doc_stats[s.doctor_id]["booked_slots"] += s.booked_slots
        doc_stats[s.doctor_id]["schedule_days"].add(s.schedule_date)

    items = []
    for doctor_id, d in doctor_map.items():
        stats = doc_stats[doctor_id]
        total = stats["total_slots"]
        booked = stats["booked_slots"]
        rate = round(booked / total * 100, 1) if total > 0 else 0.0
        items.append({
            "doctor_id": doctor_id,
            "doctor_name": d.name,
            "department_name": d.department.name if d.department else None,
            "total_slots": total,
            "booked_slots": booked,
            "completed_appointments": completed_map.get(doctor_id, 0),
            "utilization_rate": rate,
            "schedule_days": len(stats["schedule_days"]),
        })

    # 按利用率降序排列
    items.sort(key=lambda x: x["utilization_rate"], reverse=True)

    return DoctorWorkloadResponse(
        store_id=store_id,
        store_name=store.name,
        start_date=start_date,
        end_date=end_date,
        items=items
    )


@router.get(
    "/statistics/peak-hours",
    response_model=PeakHourHeatmapResponse,
    summary="高峰时段热力图",
    description="""
    获取指定门店在某日期范围内的预约高峰时段热力图数据。

    **参数说明**：
    - store_id: 门店ID（门店管理员自动取本门店，超级管理员必填）
    - start_date: 开始日期（必填）
    - end_date: 结束日期（必填）

    **返回数据**：
    - X轴: 星期（1-7），Y轴: 小时（0-23），值: 预约率
    - 基于 start_time 的小时和 schedule_date 的星期进行聚合
    """,
)
async def get_peak_hours(
    store_id: str | None = Query(None, description="门店ID"),
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:read"))
):
    """高峰时段热力图"""
    # 门店过滤
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter
    elif not store_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择门店")

    if not check_store_access(current_admin, store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权访问此门店数据")

    store_result = await db.execute(select(Store).where(Store.id == store_id))
    store = store_result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="门店不存在")

    # 查询排班数据
    schedule_result = await db.execute(
        select(Schedule).where(
            and_(
                Schedule.store_id == store_id,
                Schedule.schedule_date >= start_date,
                Schedule.schedule_date <= end_date,
                Schedule.status == 1,
            )
        )
    )
    schedules = schedule_result.scalars().all()

    cell_stats = defaultdict(lambda: {"total_slots": 0, "booked_slots": 0})

    for s in schedules:
        day_of_week = s.schedule_date.isoweekday()  # 1=周一 ... 7=周日
        hour = s.start_time.hour if s.start_time else (
            8 if s.time_slot == "morning" else (
                14 if s.time_slot == "afternoon" else (
                    19 if s.time_slot == "evening" else 0
                )
            )
        )
        key = (day_of_week, hour)
        cell_stats[key]["total_slots"] += s.total_slots
        cell_stats[key]["booked_slots"] += s.booked_slots

    cells = []
    for day_of_week in range(1, 8):
        for hour in range(24):
            key = (day_of_week, hour)
            stats = cell_stats.get(key, {"total_slots": 0, "booked_slots": 0})
            total = stats["total_slots"]
            booked = stats["booked_slots"]
            rate = round(booked / total * 100, 1) if total > 0 else 0.0
            cells.append({
                "day_of_week": day_of_week,
                "hour": hour,
                "total_slots": total,
                "booked_slots": booked,
                "booking_rate": rate,
            })

    return PeakHourHeatmapResponse(
        store_id=store_id,
        store_name=store.name,
        start_date=start_date,
        end_date=end_date,
        cells=cells
    )
