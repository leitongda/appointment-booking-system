"""数据统计 - 概览与门店 Dashboard"""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_store_filter, get_tenant_filter
from app.common.data_scope import apply_data_scope
from app.common.feature_deps import require_feature
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.store import Store
from app.models.user import Patient
from app.modules.revenue.service import RevenueService
from app.modules.statistics.helpers import _build_tenant_condition
from app.schemas.response import ResponseModel

router = APIRouter()


@router.get("/overview", response_model=ResponseModel, summary="获取概览数据")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    tenant_id: str | None = Depends(get_tenant_filter),
    _feature_guard: None = Depends(require_feature("basic_statistics", get_current_admin)),
):
    """获取概览数据（受 basic_statistics 功能开关控制）"""
    today = date.today()

    # 使用 DataScope 统一过滤（无 DataScope 时 fallback 到旧逻辑）
    admin_dict = current_admin if isinstance(current_admin, dict) else current_admin

    # 租户锚点：平台管理员为 None（全平台），租户管理员为本租户（R1-3）
    doctor_tenant_cond = _build_tenant_condition(Doctor, tenant_id)

    # 今日预约数（通过 Doctor 关联门店过滤）
    today_query = (
        select(func.count(Appointment.id))
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .where(
            and_(
                Appointment.created_at >= datetime.combine(today, datetime.min.time()),
                Appointment.created_at < datetime.combine(today + timedelta(days=1), datetime.min.time()),
            )
        )
    )
    if doctor_tenant_cond is not None:
        today_query = today_query.where(doctor_tenant_cond)
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
    if doctor_tenant_cond is not None:
        today_visits_query = today_visits_query.where(doctor_tenant_cond)
    today_visits_query = apply_data_scope(today_visits_query, Doctor, admin_dict)
    today_visits = await db.scalar(today_visits_query)

    # 总患者数（按门店过滤）
    patients_query = select(func.count(Patient.id))
    patient_tenant_cond = _build_tenant_condition(Patient, tenant_id)
    if patient_tenant_cond is not None:
        patients_query = patients_query.where(patient_tenant_cond)
    patients_query = apply_data_scope(patients_query, Patient, admin_dict)
    total_patients = await db.scalar(patients_query)

    # 总医生数（按门店过滤）
    doctors_query = select(func.count(Doctor.id)).where(Doctor.status == 1, Doctor.deleted_at.is_(None))
    if doctor_tenant_cond is not None:
        doctors_query = doctors_query.where(doctor_tenant_cond)
    doctors_query = apply_data_scope(doctors_query, Doctor, admin_dict)
    total_doctors = await db.scalar(doctors_query)

    # 本月预约数（按门店过滤）
    first_day_of_month = today.replace(day=1)
    month_query = (
        select(func.count(Appointment.id))
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .where(Appointment.created_at >= datetime.combine(first_day_of_month, datetime.min.time()))
    )
    if doctor_tenant_cond is not None:
        month_query = month_query.where(doctor_tenant_cond)
    month_query = apply_data_scope(month_query, Doctor, admin_dict)
    month_appointments = await db.scalar(month_query)

    # 本月收入（诊费）- 按门店过滤（get_store_filter 已支持 DataScope）
    revenue_service = RevenueService(db)
    store_filter = get_store_filter(admin_dict)
    month_revenue = await revenue_service.calculate_total_revenue(
        start_date=first_day_of_month,
        end_date=today,
        store_id=store_filter if isinstance(store_filter, str) else None,
        tenant_id=tenant_id,
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
    current_admin = Depends(get_current_admin),
    tenant_id: str | None = Depends(get_tenant_filter),
    _feature_guard: None = Depends(require_feature("basic_statistics", get_current_admin)),
):
    """获取门店专属Dashboard统计数据（受 basic_statistics 功能开关控制）

    包含：
    - 用户统计：总用户数、今日新增、昨日新增、本周新增、上周新增、周环比
    - 访客统计：今日PV/UV、昨日PV/UV、周环比（基于行为日志）
    - 预约统计：今日预约、昨日预约、累计签到
    """

    from app.models.behavior_log import UserBehaviorLog

    # 权限检查
    if not current_admin.get("is_super_admin"):
        admin_store_ids = current_admin.get("store_ids", [])
        if store_id not in admin_store_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权查看此门店的统计数据"
            )

    # 租户校验（R1-3）：门店必须属于当前管理员租户，平台管理员不限制
    if tenant_id is not None:
        store = await db.get(Store, store_id)
        if not store or store.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权查看此门店的统计数据"
            )

    behavior_tenant_cond = _build_tenant_condition(UserBehaviorLog, tenant_id)

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
    # 注意：UserBehaviorLog 没有 store_id 字段，只能按租户维度过滤（R1-3）

    async def _pv_count(metric, start_at: datetime, end_at: datetime) -> int:
        query = select(metric).where(
            UserBehaviorLog.event_type == "page_view",
            UserBehaviorLog.created_at >= start_at,
            UserBehaviorLog.created_at < end_at,
        )
        if behavior_tenant_cond is not None:
            query = query.where(behavior_tenant_cond)
        return await db.scalar(query) or 0

    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today + timedelta(days=1), datetime.min.time())
    yesterday_start = datetime.combine(yesterday, datetime.min.time())
    week_start_dt = datetime.combine(week_start, datetime.min.time())
    week_end_dt = datetime.combine(week_end + timedelta(days=1), datetime.min.time())
    last_week_start_dt = datetime.combine(last_week_start, datetime.min.time())
    last_week_end_dt = datetime.combine(last_week_end + timedelta(days=1), datetime.min.time())

    today_pv = await _pv_count(func.count(UserBehaviorLog.id), today_start, today_end)
    today_uv = await _pv_count(
        func.count(func.distinct(UserBehaviorLog.session_id)), today_start, today_end
    )
    yesterday_pv = await _pv_count(func.count(UserBehaviorLog.id), yesterday_start, today_start)
    yesterday_uv = await _pv_count(
        func.count(func.distinct(UserBehaviorLog.session_id)), yesterday_start, today_start
    )
    week_pv = await _pv_count(func.count(UserBehaviorLog.id), week_start_dt, week_end_dt)
    week_uv = await _pv_count(
        func.count(func.distinct(UserBehaviorLog.session_id)), week_start_dt, week_end_dt
    )
    last_week_pv = await _pv_count(
        func.count(UserBehaviorLog.id), last_week_start_dt, last_week_end_dt
    )
    last_week_uv = await _pv_count(
        func.count(func.distinct(UserBehaviorLog.session_id)), last_week_start_dt, last_week_end_dt
    )

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
                Appointment.created_at >= datetime.combine(today, datetime.min.time()),
                Appointment.created_at < datetime.combine(today + timedelta(days=1), datetime.min.time()),
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
                Appointment.created_at >= datetime.combine(yesterday, datetime.min.time()),
                Appointment.created_at < datetime.combine(today, datetime.min.time()),
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
