"""数据统计 API"""
from datetime import date, timedelta
from typing import List, Optional, Union

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_store_filter
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.store import Store
from app.models.user import Patient
from app.schemas.response import ResponseModel
from app.db.session import get_db
from app.modules.revenue.service import RevenueService
from app.modules.appointments.common import APPOINTMENT_STATUS

router = APIRouter()


def _build_store_filter_condition(store_filter: Union[None, str, List[str]]):
    """构建门店过滤条件"""
    if store_filter is None:
        return None
    if isinstance(store_filter, list):
        return Doctor.store_id.in_(store_filter)
    return Doctor.store_id == store_filter


@router.get("/overview", response_model=ResponseModel, summary="获取概览数据")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取概览数据"""
    today = date.today()
    
    # 获取门店过滤条件
    store_filter = get_store_filter(current_admin)
    store_condition = _build_store_filter_condition(store_filter)
    
    # 今日预约数（通过 Doctor 关联门店过滤）
    today_query = (
        select(func.count(Appointment.id))
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .where(func.date(Appointment.created_at) == today)
    )
    if store_condition is not None:
        today_query = today_query.where(store_condition)
    today_appointments = await db.scalar(today_query)
    
    # 今日就诊数 - 通过 Schedule 获取 schedule_date
    today_visits_query = (
        select(func.count(Appointment.id))
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .where(
            and_(
                Schedule.schedule_date == today,
                Appointment.status == 5  # 已完成
            )
        )
    )
    if store_condition is not None:
        today_visits_query = today_visits_query.where(store_condition)
    today_visits = await db.scalar(today_visits_query)
    
    # 总患者数（患者是全局的，不按门店过滤）
    total_patients = await db.scalar(
        select(func.count(Patient.id))
    )
    
    # 总医生数（按门店过滤）
    doctors_query = select(func.count(Doctor.id)).where(Doctor.status == 1, Doctor.deleted_at.is_(None))
    if store_condition is not None:
        doctors_query = doctors_query.where(store_condition)
    total_doctors = await db.scalar(doctors_query)
    
    # 本月预约数（按门店过滤）
    first_day_of_month = today.replace(day=1)
    month_query = (
        select(func.count(Appointment.id))
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .where(func.date(Appointment.created_at) >= first_day_of_month)
    )
    if store_condition is not None:
        month_query = month_query.where(store_condition)
    month_appointments = await db.scalar(month_query)
    
    # 本月收入（诊费）- 按门店过滤
    revenue_service = RevenueService(db)
    month_revenue = await revenue_service.calculate_total_revenue(
        start_date=first_day_of_month,
        end_date=today,
        store_id=store_filter if isinstance(store_filter, str) else None
    )
    
    return ResponseModel(data={
        "todayAppointments": today_appointments or 0,
        "todayVisits": today_visits or 0,
        "totalPatients": total_patients or 0,
        "totalDoctors": total_doctors or 0,
        "monthAppointments": month_appointments or 0,
        "monthRevenue": float(month_revenue),
    })


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
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
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


@router.get("/departments/ranking", response_model=ResponseModel, summary="获取科室预约排行")
async def get_department_ranking(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取科室预约排行"""
    # 获取门店过滤条件
    store_filter = get_store_filter(current_admin)
    store_condition = _build_store_filter_condition(store_filter)
    
    # Appointment -> Schedule -> Doctor -> Department
    query = (
        select(
            Department.id,
            Department.name,
            func.count(Appointment.id).label('count')
        )
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .join(Department, Doctor.department_id == Department.id)
    )
    
    if store_condition is not None:
        query = query.where(store_condition)
    
    query = query.group_by(Department.id, Department.name).order_by(
        func.count(Appointment.id).desc()
    ).limit(limit)
    
    result = await db.execute(query)
    
    data = [
        {"departmentId": row.id, "departmentName": row.name, "count": row.count}
        for row in result.fetchall()
    ]
    
    return ResponseModel(data=data)


@router.get("/doctors/ranking", response_model=ResponseModel, summary="获取医生预约排行")
async def get_doctor_ranking(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取医生预约排行"""
    # 获取门店过滤条件
    store_filter = get_store_filter(current_admin)
    store_condition = _build_store_filter_condition(store_filter)
    
    query = (
        select(
            Doctor.id,
            Doctor.name,
            Doctor.title,
            Department.name.label('department_name'),
            func.count(Appointment.id).label('count')
        )
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .join(Department, Doctor.department_id == Department.id)
    )
    
    if store_condition is not None:
        query = query.where(store_condition)
    
    query = query.group_by(
        Doctor.id, Doctor.name, Doctor.title, Department.name
    ).order_by(
        func.count(Appointment.id).desc()
    ).limit(limit)
    
    result = await db.execute(query)
    
    data = [
        {
            "doctorId": row.id,
            "doctorName": row.name,
            "title": row.title,
            "departmentName": row.department_name,
            "count": row.count
        }
        for row in result.fetchall()
    ]
    
    return ResponseModel(data=data)


@router.get("/time-slots/distribution", response_model=ResponseModel, summary="获取时段分布统计")
async def get_time_slot_distribution(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取时段分布统计"""
    # 获取门店过滤条件
    store_filter = get_store_filter(current_admin)
    store_condition = _build_store_filter_condition(store_filter)
    
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
    current_admin = Depends(get_current_admin)
):
    """获取星期分布统计"""
    # 获取门店过滤条件
    store_filter = get_store_filter(current_admin)
    store_condition = _build_store_filter_condition(store_filter)
    
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


@router.get("/revenue/trend", response_model=ResponseModel, summary="获取收入趋势")
async def get_revenue_trend(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取收入趋势"""
    today = date.today()
    start_date = today - timedelta(days=days - 1)
    
    # 获取门店过滤条件
    store_filter = get_store_filter(current_admin)
    store_condition = _build_store_filter_condition(store_filter)
    
    # 通过诊费系统计算收入
    revenue_service = RevenueService(db)
    data = await revenue_service.calculate_revenue_trend(
        start_date=start_date,
        end_date=today,
        store_id=store_filter if isinstance(store_filter, str) else None
    )
    
    trend = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        trend.append({
            "date": str(d),
            "revenue": data.get(str(d), 0)
        })
    
    return ResponseModel(data=trend)


@router.get("/appointments/summary", response_model=ResponseModel, summary="获取预约汇总统计")
async def get_appointment_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    store_id: Optional[str] = None,
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


@router.get("/stores/ranking", response_model=ResponseModel, summary="获取门店预约排行")
async def get_store_ranking(
    limit: int = Query(default=10, ge=1, le=50),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取门店预约排行（只有超管可以看到所有门店排行）"""
    # 获取门店过滤条件
    store_filter = get_store_filter(current_admin)
    store_condition = _build_store_filter_condition(store_filter)
    
    query = (
        select(
            Store.id,
            Store.name,
            func.count(Appointment.id).label('count')
        )
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .join(Store, Doctor.store_id == Store.id)
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
    
    query = query.group_by(Store.id, Store.name).order_by(
        func.count(Appointment.id).desc()
    ).limit(limit)
    
    result = await db.execute(query)
    
    data = [
        {"storeId": row.id, "storeName": row.name, "count": row.count}
        for row in result.fetchall()
    ]

    return ResponseModel(data=data)


@router.get("/store-dashboard", response_model=ResponseModel, summary="获取门店专属Dashboard统计")
async def get_store_dashboard(
    store_id: str = Query(..., description="门店ID"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取门店专属Dashboard统计数据

    包含：
    - 用户统计：总用户数、今日新增、昨日新增、本周新增、上周新增、周环比
    - 访客统计：今日PV/UV、昨日PV/UV、周环比（基于行为日志）
    - 预约统计：今日预约、昨日预约、累计签到
    """
    from app.models.behavior_log import UserBehaviorLog
    from datetime import datetime

    # 权限检查
    if not current_admin.get("is_super_admin"):
        admin_store_ids = current_admin.get("store_ids", [])
        if store_id not in admin_store_ids:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权查看此门店的统计数据"
            )

    today = date.today()
    yesterday = today - timedelta(days=1)

    # 计算本周和上周的日期范围
    week_start = today - timedelta(days=today.weekday())  # 本周一
    week_end = week_start + timedelta(days=6)  # 本周日
    last_week_start = week_start - timedelta(days=7)  # 上周一
    last_week_end = week_start - timedelta(days=1)  # 上周日

    # ========== 用户统计 ==========
    # 总用户数（按门店过滤）
    total_patients = await db.scalar(
        select(func.count(Patient.id)).where(Patient.store_id == store_id)
    ) or 0

    # 今日新增用户
    today_new_patients = await db.scalar(
        select(func.count(Patient.id)).where(
            and_(
                Patient.store_id == store_id,
                func.date(Patient.created_at) == today
            )
        )
    ) or 0

    # 昨日新增用户
    yesterday_new_patients = await db.scalar(
        select(func.count(Patient.id)).where(
            and_(
                Patient.store_id == store_id,
                func.date(Patient.created_at) == yesterday
            )
        )
    ) or 0

    # 本周新增用户
    week_new_patients = await db.scalar(
        select(func.count(Patient.id)).where(
            and_(
                Patient.store_id == store_id,
                func.date(Patient.created_at) >= week_start,
                func.date(Patient.created_at) <= week_end
            )
        )
    ) or 0

    # 上周新增用户
    last_week_new_patients = await db.scalar(
        select(func.count(Patient.id)).where(
            and_(
                Patient.store_id == store_id,
                func.date(Patient.created_at) >= last_week_start,
                func.date(Patient.created_at) <= last_week_end
            )
        )
    ) or 0

    # 用户周环比
    user_week_growth_rate = 0.0
    if last_week_new_patients > 0:
        user_week_growth_rate = round((week_new_patients - last_week_new_patients) / last_week_new_patients * 100, 1)
    elif week_new_patients > 0:
        user_week_growth_rate = 100.0

    # ========== 访客统计 ==========
    # 注意：UserBehaviorLog 没有 store_id 字段，暂时使用全局数据
    # 后续可以通过 extra_data 中的 store_id 或 page_path 来过滤

    # 今日 PV
    today_pv = await db.scalar(
        select(func.count(UserBehaviorLog.id)).where(
            and_(
                UserBehaviorLog.event_type == "page_view",
                func.date(UserBehaviorLog.created_at) == today
            )
        )
    ) or 0

    # 今日 UV
    today_uv = await db.scalar(
        select(func.count(func.distinct(UserBehaviorLog.session_id))).where(
            and_(
                UserBehaviorLog.event_type == "page_view",
                func.date(UserBehaviorLog.created_at) == today
            )
        )
    ) or 0

    # 昨日 PV
    yesterday_pv = await db.scalar(
        select(func.count(UserBehaviorLog.id)).where(
            and_(
                UserBehaviorLog.event_type == "page_view",
                func.date(UserBehaviorLog.created_at) == yesterday
            )
        )
    ) or 0

    # 昨日 UV
    yesterday_uv = await db.scalar(
        select(func.count(func.distinct(UserBehaviorLog.session_id))).where(
            and_(
                UserBehaviorLog.event_type == "page_view",
                func.date(UserBehaviorLog.created_at) == yesterday
            )
        )
    ) or 0

    # 本周 PV
    week_pv = await db.scalar(
        select(func.count(UserBehaviorLog.id)).where(
            and_(
                UserBehaviorLog.event_type == "page_view",
                func.date(UserBehaviorLog.created_at) >= week_start,
                func.date(UserBehaviorLog.created_at) <= week_end
            )
        )
    ) or 0

    # 上周 PV
    last_week_pv = await db.scalar(
        select(func.count(UserBehaviorLog.id)).where(
            and_(
                UserBehaviorLog.event_type == "page_view",
                func.date(UserBehaviorLog.created_at) >= last_week_start,
                func.date(UserBehaviorLog.created_at) <= last_week_end
            )
        )
    ) or 0

    # 本周 UV
    week_uv = await db.scalar(
        select(func.count(func.distinct(UserBehaviorLog.session_id))).where(
            and_(
                UserBehaviorLog.event_type == "page_view",
                func.date(UserBehaviorLog.created_at) >= week_start,
                func.date(UserBehaviorLog.created_at) <= week_end
            )
        )
    ) or 0

    # 上周 UV
    last_week_uv = await db.scalar(
        select(func.count(func.distinct(UserBehaviorLog.session_id))).where(
            and_(
                UserBehaviorLog.event_type == "page_view",
                func.date(UserBehaviorLog.created_at) >= last_week_start,
                func.date(UserBehaviorLog.created_at) <= last_week_end
            )
        )
    ) or 0

    # PV 周环比
    pv_week_growth_rate = 0.0
    if last_week_pv > 0:
        pv_week_growth_rate = round((week_pv - last_week_pv) / last_week_pv * 100, 1)
    elif week_pv > 0:
        pv_week_growth_rate = 100.0

    # UV 周环比
    uv_week_growth_rate = 0.0
    if last_week_uv > 0:
        uv_week_growth_rate = round((week_uv - last_week_uv) / last_week_uv * 100, 1)
    elif week_uv > 0:
        uv_week_growth_rate = 100.0

    # ========== 预约统计 ==========
    # 今日预约数
    today_appointments = await db.scalar(
        select(func.count(Appointment.id))
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .where(
            and_(
                Doctor.store_id == store_id,
                func.date(Appointment.created_at) == today
            )
        )
    ) or 0

    # 昨日预约数
    yesterday_appointments = await db.scalar(
        select(func.count(Appointment.id))
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .where(
            and_(
                Doctor.store_id == store_id,
                func.date(Appointment.created_at) == yesterday
            )
        )
    ) or 0

    # 累计签到数：统计真实已到院/接诊/完成状态，兼容历史遗留 WAITING(3) 数据
    total_checkins = await db.scalar(
        select(func.count(Appointment.id))
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .where(
            and_(
                Doctor.store_id == store_id,
                Appointment.status.in_([2, 3, 4, 5])
            )
        )
    ) or 0

    return ResponseModel(data={
        "users": {
            "total": total_patients,
            "todayNew": today_new_patients,
            "yesterdayNew": yesterday_new_patients,
            "weekNew": week_new_patients,
            "lastWeekNew": last_week_new_patients,
            "weekGrowthRate": user_week_growth_rate,
        },
        "visitors": {
            "todayPV": today_pv,
            "todayUV": today_uv,
            "yesterdayPV": yesterday_pv,
            "yesterdayUV": yesterday_uv,
            "pvWeekGrowthRate": pv_week_growth_rate,
            "uvWeekGrowthRate": uv_week_growth_rate,
        },
        "appointments": {
            "todayCount": today_appointments,
            "yesterdayCount": yesterday_appointments,
            "totalCheckins": total_checkins,
        },
    })


@router.get("/retention", response_model=ResponseModel, summary="获取用户留存率")
async def get_retention_rate(
    store_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    cohort: str = Query(default="month", regex="^(day|week|month)$"),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """获取用户留存率（按 cohort 分组，统计后续重复预约比例）"""
    if not start_date:
        start_date = date.today() - timedelta(days=180)
    if not end_date:
        end_date = date.today()

    # 门店过滤
    store_filter = get_store_filter(current_admin)
    store_cond = None
    if store_filter is not None:
        store_cond = _build_store_filter_condition(store_filter)
    elif store_id:
        store_cond = Doctor.store_id == store_id

    # cohort 间隔
    if cohort == "day":
        bucket_fn = func.date(Appointment.created_at)
        bucket_label = func.to_char(func.date(Appointment.created_at), 'YYYY-MM-DD')
    elif cohort == "week":
        bucket_fn = func.date_trunc('week', Appointment.created_at)
        bucket_label = func.to_char(func.date_trunc('week', Appointment.created_at), 'YYYY-MM-DD')
    else:  # month
        bucket_fn = func.date_trunc('month', Appointment.created_at)
        bucket_label = func.to_char(func.date_trunc('month', Appointment.created_at), 'YYYY-MM')

    # Step 1: 每个 cohort 的首次预约用户
    first_appt_subq = (
        select(
            Appointment.user_id,
            func.min(bucket_fn).label("first_bucket"),
        )
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .where(
            and_(
                Appointment.created_at >= start_date,
                Appointment.created_at <= end_date,
            )
        )
    )
    if store_cond is not None:
        first_appt_subq = first_appt_subq.where(store_cond)
    first_appt_subq = first_appt_subq.group_by(Appointment.user_id).subquery()

    # Step 2: 统计每个 cohort 的用户数
    cohort_users = (
        select(
            first_appt_subq.c.first_bucket.label("cohort_bucket"),
            func.count(func.distinct(first_appt_subq.c.user_id)).label("cohort_size"),
        )
        .group_by(first_appt_subq.c.first_bucket)
        .order_by(first_appt_subq.c.first_bucket)
    )
    cohort_result = await db.execute(cohort_users)
    cohort_rows = cohort_result.all()

    # Step 3: 统计每个 cohort 用户在后续 bucket 中的回访数
    all_appt_subq = (
        select(
            Appointment.user_id,
            bucket_fn.label("appt_bucket"),
        )
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .where(
            and_(
                Appointment.created_at >= start_date,
                Appointment.created_at <= end_date,
            )
        )
    )
    if store_cond is not None:
        all_appt_subq = all_appt_subq.where(store_cond)
    all_appt_subq = all_appt_subq.group_by(Appointment.user_id, bucket_fn).subquery()

    retention_data = []
    for row in cohort_rows:
        cohort_bucket = row.cohort_bucket
        cohort_size = row.cohort_size

        # 统计该 cohort 用户在后续 bucket 中的回访数
        retention_query = (
            select(
                func.count(func.distinct(all_appt_subq.c.user_id)).label("retained"),
            )
            .select_from(first_appt_subq)
            .join(all_appt_subq, first_appt_subq.c.user_id == all_appt_subq.c.user_id)
            .where(
                and_(
                    first_appt_subq.c.first_bucket == cohort_bucket,
                    all_appt_subq.c.appt_bucket > cohort_bucket,
                )
            )
        )
        retained = await db.scalar(retention_query) or 0

        retention_data.append({
            "cohort": str(cohort_bucket)[:10] if hasattr(cohort_bucket, 'isoformat') else str(cohort_bucket),
            "cohortSize": cohort_size,
            "retained": retained,
            "retentionRate": round(retained / cohort_size * 100, 2) if cohort_size > 0 else 0,
        })

    return ResponseModel(data=retention_data)


@router.get("/revisit-rate", response_model=ResponseModel, summary="获取复诊率")
async def get_revisit_rate(
    store_id: Optional[str] = None,
    doctor_id: Optional[str] = None,
    department_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """获取复诊率（同一用户在同一医生/科室的重复就诊比例）"""
    if not start_date:
        start_date = date.today() - timedelta(days=90)
    if not end_date:
        end_date = date.today()

    # 门店过滤
    store_filter = get_store_filter(current_admin)
    conditions = [
        Appointment.status == 5,  # 已完成
        Appointment.created_at >= start_date,
        Appointment.created_at <= end_date,
    ]

    if store_filter is not None:
        store_cond = _build_store_filter_condition(store_filter)
        if store_cond is not None:
            conditions.append(store_cond)
    elif store_id:
        conditions.append(Doctor.store_id == store_id)

    if doctor_id:
        conditions.append(Doctor.id == doctor_id)
    if department_id:
        conditions.append(Department.id == department_id)

    # 按用户+医生统计就诊次数
    user_doctor_query = (
        select(
            Appointment.user_id,
            Doctor.id.label("doctor_id"),
            func.count(Appointment.id).label("visit_count"),
        )
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .join(Department, Doctor.department_id == Department.id)
        .where(and_(*conditions))
        .group_by(Appointment.user_id, Doctor.id)
    )
    result = await db.execute(user_doctor_query)
    rows = result.all()

    total_user_doctor_pairs = len(rows)
    revisit_pairs = sum(1 for r in rows if r.visit_count > 1)
    total_visits = sum(r.visit_count for r in rows)
    revisit_visits = sum(r.visit_count - 1 for r in rows if r.visit_count > 1)

    # 按用户统计（跨医生）
    user_query = (
        select(
            Appointment.user_id,
            func.count(Appointment.id).label("visit_count"),
        )
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .join(Department, Doctor.department_id == Department.id)
        .where(and_(*conditions))
        .group_by(Appointment.user_id)
    )
    user_result = await db.execute(user_query)
    user_rows = user_result.all()

    total_users = len(user_rows)
    revisit_users = sum(1 for r in user_rows if r.visit_count > 1)

    return ResponseModel(data={
        "overall": {
            "totalUsers": total_users,
            "revisitUsers": revisit_users,
            "revisitRate": round(revisit_users / total_users * 100, 2) if total_users > 0 else 0,
        },
        "byDoctor": {
            "totalPairs": total_user_doctor_pairs,
            "revisitPairs": revisit_pairs,
            "revisitRate": round(revisit_pairs / total_user_doctor_pairs * 100, 2) if total_user_doctor_pairs > 0 else 0,
        },
        "visits": {
            "totalVisits": total_visits,
            "revisitVisits": revisit_visits,
            "revisitRatio": round(revisit_visits / total_visits * 100, 2) if total_visits > 0 else 0,
        },
        "params": {
            "startDate": str(start_date),
            "endDate": str(end_date),
            "storeId": store_id,
            "doctorId": doctor_id,
            "departmentId": department_id,
        },
    })
