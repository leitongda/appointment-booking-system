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
    doctors_query = select(func.count(Doctor.id)).where(Doctor.status == 1)
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
        3: "候诊中",
        4: "就诊中",
        5: "已完成",
        6: "已取消",
        7: "已过期",
        8: "已关闭",
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
            func.sum(case((Appointment.status == 5, 1), else_=0)).label('completed'),
            func.sum(case((Appointment.status == 8, 1), else_=0)).label('no_show'),  # 8=CLOSED(爽约)
            func.sum(case((Appointment.status == 6, 1), else_=0)).label('cancelled'),
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

    # 累计签到数（status >= 2 表示已签到）
    total_checkins = await db.scalar(
        select(func.count(Appointment.id))
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .where(
            and_(
                Doctor.store_id == store_id,
                Appointment.status >= 2  # 已签到、候诊中、就诊中、已完成
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
