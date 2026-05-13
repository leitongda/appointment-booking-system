from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract
from typing import Optional, List
from datetime import date, datetime, timezone
from calendar import monthrange
from pydantic import BaseModel, Field
import pytz
import logging

from app.db.session import get_db

logger = logging.getLogger(__name__)
from app.api.deps import get_current_admin, get_store_filter, check_store_access, require_permission
from app.schemas.schedule import ScheduleCreate, ScheduleBatchCreate, ScheduleUpdate, ScheduleResponse, AvailableScheduleResponse, CustomScheduleCreate, CustomScheduleResponse, UtilizationTrendResponse, DoctorWorkloadResponse, PeakHourHeatmapResponse
from app.schemas.response import PageResponse
from app.modules.schedules.service import ScheduleService

from app.modules.rule_engine import RuleEngineService
from app.models.schedule import Schedule
from app.models.doctor import Doctor
from app.models.store import Store
from app.models.rest_day import RestDay
from app.core.config import settings
import json

router = APIRouter()


class BatchOperateResponse(BaseModel):
    """批量操作响应"""
    success: bool
    affected_count: int
    message: str


async def _check_single_schedule_rest_day(
    db: AsyncSession,
    schedule_date: date,
    store_id: Optional[str],
    doctor_id: str
) -> bool:
    """检查单个排班是否在休息日"""
    rest_day_result = await db.execute(
        select(RestDay).where(
            and_(
                RestDay.status == 1,
                RestDay.start_date <= schedule_date,
                RestDay.end_date >= schedule_date
            )
        )
    )
    rest_days = rest_day_result.scalars().all()

    for rd in rest_days:
        # 检查门店是否匹配
        if store_id and rd.store_id != store_id:
            continue
        # 如果 doctor_ids 为空，表示门店所有医生休息
        if rd.doctor_ids is None:
            return True
        # 检查医生是否在休息日列表中
        try:
            doctor_ids_list = json.loads(rd.doctor_ids)
            if doctor_id in doctor_ids_list:
                return True
        except:
            pass
    return False


def _check_rest_day_for_schedule(
    schedule_date: date,
    store_id: Optional[str],
    doctor_id: str,
    rest_days: list
) -> bool:
    """检查指定排班是否在休息日（基于已查询的休息日列表）"""
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
            doctor_ids_list = json.loads(rd.doctor_ids)
            if doctor_id in doctor_ids_list:
                return True
        except:
            pass
    return False


class SuspendRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=200, description="停诊原因")
    notify_patients: bool = Field(True, description="是否通知患者")

@router.get(
    "",
    response_model=PageResponse[ScheduleResponse],
    summary="获取排班列表",
    description="""
    获取排班列表（管理端），支持分页和多条件筛选。

    **支持筛选条件**：
    - doctor_id: 按医生筛选
    - store_id: 按门店筛选
    - start_date / end_date: 按排班日期范围筛选
    - status: 按状态筛选（1=正常 0=停诊）

    **数据隔离**：
    - 门店管理员只能查看本门店的排班

    **返回数据**：
    - 包含医生姓名、科室名称等关联信息
    - 包含 is_rest_day 字段，标记该排班日期是否在休息日范围内
    - 休息日判断逻辑：全局休息日 + 门店级休息日 + 医生级休息日
    """,
)
async def get_schedules(
    doctor_id: Optional[str] = None,
    store_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取排班列表"""
    # 门店过滤
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter
    
    service = ScheduleService(db)
    schedules, total = await service.get_list(
        doctor_id=doctor_id, store_id=store_id, start_date=start_date, end_date=end_date,
        status=status, page=page, page_size=page_size
    )
    
    # 查询日期范围内的所有有效休息日（用于计算 is_rest_day）
    rest_days = []
    if schedules and (start_date or end_date):
        query_start = start_date or min(s.schedule_date for s in schedules)
        query_end = end_date or max(s.schedule_date for s in schedules)
        rest_day_result = await db.execute(
            select(RestDay).where(
                and_(
                    RestDay.status == 1,
                    RestDay.start_date <= query_end,
                    RestDay.end_date >= query_start
                )
            )
        )
        rest_days = rest_day_result.scalars().all()
    
    def check_rest_day(schedule_date, schedule_store_id, schedule_doctor_id) -> bool:
        """检查指定排班是否在休息日"""
        for rd in rest_days:
            # 检查日期是否在休息日范围内
            if not (rd.start_date <= schedule_date <= rd.end_date):
                continue
            # 检查门店是否匹配
            if schedule_store_id and rd.store_id != schedule_store_id:
                continue
            # 如果 doctor_ids 为空，表示门店所有医生休息
            if rd.doctor_ids is None:
                return True
            # 检查医生是否在休息日列表中
            try:
                doctor_ids_list = json.loads(rd.doctor_ids)
                if schedule_doctor_id in doctor_ids_list:
                    return True
            except:
                pass
        return False
    
    result = []
    for s in schedules:
        is_rest = check_rest_day(s.schedule_date, s.store_id, s.doctor_id)
        result.append(ScheduleResponse(
            id=s.id,
            doctor_id=s.doctor_id,
            store_id=s.store_id,
            doctor_name=s.doctor.name if s.doctor else None,
            department_name=s.doctor.department.name if s.doctor and s.doctor.department else None,
            schedule_date=s.schedule_date,
            time_slot=s.time_slot,
            start_time=s.start_time,
            end_time=s.end_time,
            total_slots=s.total_slots,
            booked_slots=s.booked_slots,
            appointment_type=s.appointment_type,
            template_id=s.template_id,
            status=s.status,
            created_at=s.created_at,
            is_rest_day=is_rest,
            effective_status=getattr(s, 'effective_status', 'active'),
        ))
    
    return PageResponse(data=result, total=total, page=page, page_size=page_size)


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
    items: List[ScheduleStatisticsItem]


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
    store_id: Optional[str] = Query(None, description="门店ID"),
    year: int = Query(..., ge=2020, le=2100, description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
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
    store_id: Optional[str] = Query(None, description="门店ID"),
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    granularity: str = Query("week", pattern="^(week|month)$", description="粒度: week / month"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
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

    from collections import defaultdict
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
    store_id: Optional[str] = Query(None, description="门店ID"),
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
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

    from collections import defaultdict
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
    store_id: Optional[str] = Query(None, description="门店ID"),
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
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

    from collections import defaultdict
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


@router.get(
    "/available/{doctor_id}",
    response_model=List[AvailableScheduleResponse],
    summary="获取可预约排班",
    description="""
    获取指定医生的可预约排班（公开接口，患者端使用）。

    **参数说明**：
    - doctor_id: 医生ID（路径参数）
    - store_id: 门店ID（可选，用于查询该医生的预约设置）
    - days: 查询未来天数（默认14天，最大30天，当医生有预约设置时作为 fallback）

    **返回数据**：
    - 包含规则引擎计算的预约时间窗信息（booking_open_at / booking_close_at）
    - booking_status: available（可预约）/ not_open（未开放）/ closed（已截止）/ full（约满）/ closing_soon（即将约满）
    - capacity_percent: 剩余容量百分比
    - urgency_level: 紧急程度（normal/medium/high/critical）
    - is_rest_day: 是否在休息日（此处始终为 False，因为已过滤）
    - booking_setting_applied: 是否应用了医生预约设置
    """,
)
async def get_available_schedules(
    doctor_id: str,
    store_id: Optional[str] = Query(None, description="门店ID"),
    days: int = Query(14, ge=1, le=30),
    db: AsyncSession = Depends(get_db)
):
    """获取可预约排班（增强版：包含规则引擎信息）"""
    service = ScheduleService(db)
    rule_engine = RuleEngineService(db)
    schedules, booking_setting_applied = await service.get_available(
        doctor_id, days=days, store_id=store_id
    )

    # 使用本地时区（中国标准时间）
    local_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(local_tz)
    result = []

    for s in schedules:
        available = s.total_slots - s.booked_slots

        # 检查预约时间窗（使用规则引擎）
        booking_open_at = None
        booking_close_at = None
        booking_status = "available"

        try:
            window_check = await rule_engine.check_action_window(s, 'BOOK', now)
            if window_check.get('allowed'):
                booking_open_at = window_check.get('open_at')
                booking_close_at = window_check.get('close_at')
            else:
                # 未开放或已截止
                if now < window_check.get('open_at', now):
                    booking_status = 'not_open'
                    booking_open_at = window_check.get('open_at')
                    booking_close_at = window_check.get('close_at')
                else:
                    booking_status = 'closed'
                    booking_open_at = window_check.get('open_at')
                    booking_close_at = window_check.get('close_at')
        except Exception as e:
            # 规则引擎检查失败，记录日志并使用默认状态
            logger.warning(f"规则引擎检查失败: schedule_id={s.id}, error={e}")

        # 如果已约满，覆盖状态
        if available == 0:
            booking_status = 'full'

        # 计算容量百分比
        capacity_percent = (available / s.total_slots * 100) if s.total_slots > 0 else 0

        # 判断紧急程度（按百分比：>50%正常，20-50%中等，<20%紧急，0%约满）
        urgency_level = "normal"
        if available == 0:
            urgency_level = "critical"  # 约满
        elif capacity_percent < 20:
            urgency_level = "high"
        elif capacity_percent < 50:
            urgency_level = "medium"

        # 如果即将截止（<30分钟），提升紧急程度
        if booking_close_at:
            minutes_until_close = (booking_close_at - now).total_seconds() / 60
            if 0 < minutes_until_close < 30 and booking_status == 'available':
                if urgency_level == 'normal':
                    urgency_level = 'medium'
                elif urgency_level == 'medium':
                    urgency_level = 'high'

        # 更新即将约满状态
        if booking_status == 'available' and capacity_percent < 30 and capacity_percent > 0:
            booking_status = 'closing_soon'

        # 自定义排班（template_id=None）不受休息日影响，is_rest_day 始终为 False
        # 这里的排班已经通过 get_available 过滤，所以能到这里的要么不是休息日，
        # 要么是自定义排班（不受休息日影响）
        is_rest_day_flag = False  # 已过滤，这里的排班都是可预约的

        result.append(AvailableScheduleResponse(
            id=s.id,
            schedule_date=s.schedule_date,
            time_slot=s.time_slot,
            available_slots=available,
            total_slots=s.total_slots,
            start_time=s.start_time,
            end_time=s.end_time,
            appointment_type=s.appointment_type,
            booking_open_at=booking_open_at,
            booking_close_at=booking_close_at,
            booking_status=booking_status,
            capacity_percent=round(capacity_percent, 1),
            urgency_level=urgency_level,
            template_id=s.template_id,
            is_rest_day=is_rest_day_flag,
            booking_setting_applied=booking_setting_applied,
        ))

    return result

@router.get(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    summary="获取排班详情",
    description="""
    获取排班详情（管理端接口）。

    **参数说明**：
    - schedule_id: 排班记录ID（路径参数）

    **返回数据**：
    - 包含医生姓名、科室名称等关联信息
    - 包含 is_rest_day 字段，通过休息日配置判断
    """,
)
async def get_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取排班详情"""
    service = ScheduleService(db)
    schedule = await service.get_by_id(schedule_id)
    
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排班不存在，请检查后重试")
    
    # 检查是否在休息日
    is_rest_day = await _check_single_schedule_rest_day(
        db, schedule.schedule_date, schedule.store_id, schedule.doctor_id
    )
    
    return ScheduleResponse(
        id=schedule.id,
        doctor_id=schedule.doctor_id,
        store_id=schedule.store_id,
        doctor_name=schedule.doctor.name if schedule.doctor else None,
        department_name=schedule.doctor.department.name if schedule.doctor and schedule.doctor.department else None,
        schedule_date=schedule.schedule_date,
        time_slot=schedule.time_slot,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        total_slots=schedule.total_slots,
        booked_slots=schedule.booked_slots,
        appointment_type=schedule.appointment_type,
        template_id=schedule.template_id,
        status=schedule.status,
        created_at=schedule.created_at,
        is_rest_day=is_rest_day
    )

@router.post(
    "",
    response_model=ScheduleResponse,
    summary="创建排班",
    description="""
    创建单条排班记录。

    **权限要求**：管理员权限（schedule:create）。

    **业务规则**：
    - 同一医生同一天同一时段不可重复排班
    - 需指定医生（doctor_id）、排班日期（schedule_date）、时段（time_slot）、号源数量（total_slots）
    - 创建后自动检查是否与休息日冲突，返回 is_rest_day 标记
    """,
)
async def create_schedule(
    data: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:create"))
):
    """创建排班"""
    service = ScheduleService(db)
    
    try:
        schedule = await service.create(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    # 检查是否在休息日
    is_rest_day = await _check_single_schedule_rest_day(
        db, schedule.schedule_date, schedule.store_id, schedule.doctor_id
    )
    
    return ScheduleResponse(
        id=schedule.id,
        doctor_id=schedule.doctor_id,
        store_id=schedule.store_id,
        schedule_date=schedule.schedule_date,
        time_slot=schedule.time_slot,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        total_slots=schedule.total_slots,
        booked_slots=schedule.booked_slots,
        appointment_type=schedule.appointment_type,
        template_id=schedule.template_id,
        status=schedule.status,
        created_at=schedule.created_at,
        is_rest_day=is_rest_day
    )

@router.post(
    "/batch",
    response_model=BatchOperateResponse,
    summary="批量创建排班",
    description="""
    批量创建排班记录，支持按日期范围和医生列表批量生成。

    **权限要求**：管理员权限（schedule:create）。

    **业务规则**：
    - 自动跳过已存在排班的日期/时段（不报错）
    - 休息日内的排班会自动跳过
    - 返回实际创建的排班数量（affected_count）
    """,
)
async def batch_create_schedules(
    data: ScheduleBatchCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:create"))
):
    """批量创建排班"""
    service = ScheduleService(db)
    try:
        created_count = await service.batch_create(data, operator_id=current_admin.get("id"))
        return BatchOperateResponse(
            success=True,
            affected_count=created_count,
            message=f"成功创建 {created_count} 条排班"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    summary="更新排班",
    description="""
    更新排班信息。

    **权限要求**：管理员权限（schedule:update）。

    **业务规则**：
    - 已有预约记录的排班，号源数量不可少于已预约数量（booked_slots）
    - 更新后自动检查休息日冲突

    **参数说明**：
    - schedule_id: 排班记录ID（路径参数）
    """,
)
async def update_schedule(
    schedule_id: str,
    data: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:update"))
):
    """更新排班"""
    service = ScheduleService(db)
    
    try:
        schedule = await service.update(schedule_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排班不存在，请检查后重试")
    
    # 检查是否在休息日
    is_rest_day = await _check_single_schedule_rest_day(
        db, schedule.schedule_date, schedule.store_id, schedule.doctor_id
    )
    
    return ScheduleResponse(
        id=schedule.id,
        doctor_id=schedule.doctor_id,
        store_id=schedule.store_id,
        schedule_date=schedule.schedule_date,
        time_slot=schedule.time_slot,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        total_slots=schedule.total_slots,
        booked_slots=schedule.booked_slots,
        appointment_type=schedule.appointment_type,
        template_id=schedule.template_id,
        status=schedule.status,
        created_at=schedule.created_at,
        is_rest_day=is_rest_day
    )

class BatchScheduleRequest(BaseModel):
    """批量操作排班请求"""
    schedule_ids: List[str] = Field(..., min_length=1, description="排班ID列表")
    reason: Optional[str] = Field(None, max_length=200, description="操作原因")


@router.post(
    "/batch-suspend",
    response_model=BatchOperateResponse,
    summary="批量停诊",
    description="""
    批量将排班标记为停诊状态。

    **权限要求**：管理员权限（schedule:update）。

    **业务规则**：
    - 停诊后对应排班不再对患者可见
    - 已有预约的处理由 service 层决定（通知患者等）
    - 返回实际影响的排班数量

    **参数说明**：
    - schedule_ids: 排班ID列表（必填，至少1个）
    - reason: 停诊原因（可选，最大200字）
    """,
)
async def batch_suspend_schedules(
    data: BatchScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:update"))
):
    """批量停诊排班"""
    service = ScheduleService(db)

    try:
        affected_count = await service.batch_suspend(
            data.schedule_ids,
            data.reason,
            operator_id=current_admin.get("id")
        )
        return BatchOperateResponse(
            success=True,
            affected_count=affected_count,
            message=f"成功停诊 {affected_count} 条排班记录"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/batch-resume",
    response_model=BatchOperateResponse,
    summary="批量恢复排班",
    description="""
    批量恢复已停诊的排班。

    **权限要求**：管理员权限（schedule:update）。

    **业务规则**：
    - 恢复后排班重新对患者可见
    - 只有已停诊状态的排班会受影响
    - 返回实际恢复的排班数量

    **参数说明**：
    - schedule_ids: 排班ID列表（必填，至少1个）
    """,
)
async def batch_resume_schedules(
    data: BatchScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:update"))
):
    """批量恢复排班"""
    service = ScheduleService(db)

    try:
        affected_count = await service.batch_resume(
            data.schedule_ids,
            operator_id=current_admin.get("id")
        )
        return BatchOperateResponse(
            success=True,
            affected_count=affected_count,
            message=f"成功恢复 {affected_count} 条排班记录"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/batch-delete",
    response_model=BatchOperateResponse,
    summary="批量删除排班",
    description="""
    批量删除排班记录。

    **权限要求**：管理员权限（schedule:delete）。

    **业务规则**：
    - 只能删除没有任何预约记录的排班
    - 存在预约记录的排班会自动跳过（不报错）
    - 返回消息中包含实际删除数量和跳过数量

    **参数说明**：
    - schedule_ids: 排班ID列表（必填，至少1个）
    """,
)
async def batch_delete_schedules(
    data: BatchScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:delete"))
):
    """批量删除排班（只能删除没有任何预约记录的排班）"""
    service = ScheduleService(db)
    
    try:
        affected_count = await service.batch_delete(data.schedule_ids)
        skipped = len(data.schedule_ids) - affected_count
        message = f"成功删除 {affected_count} 条排班记录"
        if skipped > 0:
            message += f"，{skipped} 条因存在预约记录而跳过"
        return BatchOperateResponse(
            success=True,
            affected_count=affected_count,
            message=message
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ========== 自定义排班端点（原 custom_schedules/router.py） ==========


@router.get(
    "/custom-schedules",
    response_model=PageResponse[CustomScheduleResponse],
    summary="获取自定义排班列表",
    description="""
    获取自定义排班列表（template_id为NULL的排班）。

    **支持筛选条件**：
    - store_id: 按门店筛选
    - department_id: 按科室筛选
    - doctor_id: 按医生筛选
    - start_date / end_date: 按排班日期范围筛选
    - appointment_type: 按预约类型筛选
    - status: 按状态筛选（1=正常 0=停诊）

    **数据隔离**：
    - 门店管理员只能查看本门店的排班
    """,
)
async def get_custom_schedules(
    store_id: Optional[str] = None,
    department_id: Optional[str] = None,
    doctor_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    appointment_type: Optional[str] = None,
    status: Optional[int] = Query(None, ge=0, le=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
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
        query = query.join(Doctor).where(Doctor.department_id == department_id, Doctor.deleted_at.is_(None))
        count_query = count_query.join(Doctor).where(Doctor.department_id == department_id, Doctor.deleted_at.is_(None))

    query = query.order_by(Schedule.schedule_date, Schedule.start_time)
    query = query.offset((page - 1) * page_size).limit(page_size)

    result_query = await db.execute(query)
    schedules = result_query.scalars().all()

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # 查询日期范围内的所有有效休息日
    rest_days = []
    if schedules and (start_date or end_date):
        query_start = start_date or min(s.schedule_date for s in schedules)
        query_end = end_date or max(s.schedule_date for s in schedules)
        rest_day_conditions = [
            RestDay.status == 1,
            RestDay.start_date <= query_end,
            RestDay.end_date >= query_start
        ]
        if store_id:
            rest_day_conditions.append(RestDay.store_id == store_id)
        rest_day_result = await db.execute(
            select(RestDay).where(and_(*rest_day_conditions))
        )
        rest_days = rest_day_result.scalars().all()

    result = []
    for s in schedules:
        is_rest = _check_rest_day_for_schedule(
            s.schedule_date, s.store_id, s.doctor_id, rest_days
        )
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
            created_at=s.created_at,
            is_rest_day=is_rest
        ))

    return PageResponse(data=result, total=total, page=page, page_size=page_size)


@router.get(
    "/custom-schedules/effective",
    response_model=List[CustomScheduleResponse],
    summary="获取生效的自定义排班",
    description="""
    获取生效的自定义排班（template_id为NULL的排班）。

    **参数说明**：
    - store_id: 门店ID（可选）
    - doctor_id: 医生ID（可选）
    - start_date: 开始日期（必填）
    - end_date: 结束日期（必填）
    """,
)
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

    # 查询日期范围内的所有有效休息日
    rest_days = []
    if schedules:
        rest_day_conditions = [
            RestDay.status == 1,
            RestDay.start_date <= end_date,
            RestDay.end_date >= start_date
        ]
        if store_id:
            rest_day_conditions.append(RestDay.store_id == store_id)
        rest_day_result = await db.execute(
            select(RestDay).where(and_(*rest_day_conditions))
        )
        rest_days = rest_day_result.scalars().all()

    result = []
    for s in schedules:
        is_rest = _check_rest_day_for_schedule(
            s.schedule_date, s.store_id, s.doctor_id, rest_days
        )
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
            created_at=s.created_at,
            is_rest_day=is_rest
        ))

    return result


@router.post(
    "/custom-schedules",
    response_model=List[CustomScheduleResponse],
    summary="创建自定义排班",
    description="""
    创建自定义排班（支持批量）。

    **权限要求**：管理员权限（schedule:create）。

    **业务规则**：
    - 支持批量创建多个日期的排班
    - 支持每个日期添加多个时段
    - 可选是否均分时段
    - 自定义排班没有模板ID（template_id为NULL）
    """,
)
async def create_custom_schedules(
    data: CustomScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:create"))
):
    """创建自定义排班（支持批量）"""
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

        # 查询日期范围内的休息日（用于计算 is_rest_day）
        rest_days = []
        if created_schedules:
            min_date = min(s.schedule_date for s in created_schedules)
            max_date = max(s.schedule_date for s in created_schedules)
            rest_day_result = await db.execute(
                select(RestDay).where(
                    and_(
                        RestDay.status == 1,
                        RestDay.start_date <= max_date,
                        RestDay.end_date >= min_date,
                        RestDay.store_id == data.store_id
                    )
                )
            )
            rest_days = rest_day_result.scalars().all()

        for s in created_schedules:
            await db.refresh(s)
            # 重新加载关联数据
            await db.refresh(s, ["doctor", "store"])
            if s.doctor:
                await db.refresh(s.doctor, ["department"])

            is_rest = _check_rest_day_for_schedule(
                s.schedule_date, s.store_id, s.doctor_id, rest_days
            )
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
                created_at=s.created_at,
                is_rest_day=is_rest
            ))

        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/custom-schedules/{schedule_id}",
    summary="删除自定义排班",
    description="""
    删除自定义排班（仅能删除template_id为NULL的排班）。

    **权限要求**：管理员权限（schedule:delete）。

    **业务规则**：
    - 只能删除自定义排班（template_id为NULL）
    - 已有预约记录的排班无法删除
    """,
)
async def delete_custom_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:delete"))
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
