"""数据统计 - 概览与门店 Dashboard"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_store_filter
from app.common.data_scope import apply_data_scope
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.user import Patient
from app.models.schedule import Schedule
from app.schemas.response import ResponseModel
from app.db.session import get_db
from app.modules.revenue.service import RevenueService
from app.modules.statistics.helpers import _build_store_filter_condition

router = APIRouter()


@router.get("/overview", response_model=ResponseModel, summary="获取概览数据")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取概览数据"""
    today = date.today()

    # 使用 DataScope 统一过滤（无 DataScope 时 fallback 到旧逻辑）
    admin_dict = current_admin if isinstance(current_admin, dict) else current_admin

    # 今日预约数（通过 Doctor 关联门店过滤）
    today_query = (
        select(func.count(Appointment.id))
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .where(func.date(Appointment.created_at) == today)
    )
    today_query = apply_data_scope(today_query, Doctor, admin_dict)
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
    today_visits_query = apply_data_scope(today_visits_query, Doctor, admin_dict)
    today_visits = await db.scalar(today_visits_query)

    # 总患者数（按门店过滤）
    patients_query = select(func.count(Patient.id))
    patients_query = apply_data_scope(patients_query, Patient, admin_dict)
    total_patients = await db.scalar(patients_query)

    # 总医生数（按门店过滤）
    doctors_query = select(func.count(Doctor.id)).where(Doctor.status == 1, Doctor.deleted_at.is_(None))
    doctors_query = apply_data_scope(doctors_query, Doctor, admin_dict)
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
    month_query = apply_data_scope(month_query, Doctor, admin_dict)
    month_appointments = await db.scalar(month_query)

    # 本月收入（诊费）- 按门店过滤（get_store_filter 已支持 DataScope）
    revenue_service = RevenueService(db)
    store_filter = get_store_filter(admin_dict)
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
