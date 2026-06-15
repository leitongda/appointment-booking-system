"""数据统计 - 用户留存与复诊率"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_store_filter
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.modules.statistics.helpers import _build_store_filter_condition
from app.schemas.response import ResponseModel

router = APIRouter()


@router.get("/retention", response_model=ResponseModel, summary="获取用户留存率")
async def get_retention_rate(
    store_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
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
    store_id: str | None = None,
    doctor_id: str | None = None,
    department_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
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
