"""预约查询相关端点"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date, timedelta
from typing import Optional, List

from app.db.session import get_db
from app.api.deps import get_current_doctor_by_token
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.modules.appointments.service import AppointmentService
from app.modules.visit_types.service import VisitTypeService
from app.modules.doctor_portal.schemas import DoctorAppointmentResponse

router = APIRouter()


@router.get("", response_model=List[DoctorAppointmentResponse], summary="获取预约列表")
async def get_my_appointments(
    status: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """获取当前医生的预约列表

    自动限制为当前医生的预约
    """
    service = AppointmentService(db)
    visit_type_service = VisitTypeService(db)

    appointments, total = await service.get_list(
        doctor_id=doctor.id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )

    result = []
    for a in appointments:
        # 判断是否为复诊
        is_follow_up = False
        if a.patient_id and doctor.department_id:
            try:
                is_follow_up = await visit_type_service.is_follow_up_visit(
                    patient_id=a.patient_id,
                    store_id=doctor.store_id,
                    doctor_id=doctor.id,
                    department_id=doctor.department_id,
                )
            except Exception:
                pass

        result.append(DoctorAppointmentResponse(
            id=a.id,
            appointment_no=a.appointment_no,
            patient_id=a.patient_id,
            patient_name=a.patient_name,
            patient_phone=a.patient_phone,
            schedule_date=a.schedule.schedule_date if a.schedule else None,
            time_slot=a.schedule.time_slot if a.schedule else None,
            queue_number=a.queue_number,
            status=a.status,
            sign_in_time=a.sign_in_time,
            call_time=a.call_time,
            complete_time=a.complete_time,
            symptom_description=a.symptom_description,
            is_follow_up=is_follow_up,
        ))

    return result


@router.get("/today", response_model=List[DoctorAppointmentResponse], summary="获取今日预约")
async def get_my_today_appointments(
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """获取当前医生今日预约"""
    service = AppointmentService(db)
    visit_type_service = VisitTypeService(db)
    appointments = await service.get_today_by_doctor(doctor.id)

    result = []
    for a in appointments:
        # 判断是否为复诊
        is_follow_up = False
        if a.patient_id and doctor.department_id:
            try:
                is_follow_up = await visit_type_service.is_follow_up_visit(
                    patient_id=a.patient_id,
                    store_id=doctor.store_id,
                    doctor_id=doctor.id,
                    department_id=doctor.department_id,
                )
            except Exception:
                pass  # 复诊判断失败不影响正常显示

        result.append(DoctorAppointmentResponse(
            id=a.id,
            appointment_no=a.appointment_no,
            patient_id=a.patient_id,
            patient_name=a.patient_name,
            patient_phone=a.patient_phone,
            schedule_date=a.schedule.schedule_date if a.schedule else None,
            time_slot=a.schedule.time_slot if a.schedule else None,
            queue_number=a.queue_number,
            status=a.status,
            sign_in_time=a.sign_in_time,
            call_time=a.call_time,
            complete_time=a.complete_time,
            symptom_description=a.symptom_description,
            is_follow_up=is_follow_up,
        ))

    return result


@router.get("/statistics/today", summary="获取今日统计")
async def get_my_today_statistics(
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """获取当前医生今日统计数据"""
    service = AppointmentService(db)
    today = date.today()

    stats = await service.get_statistics(
        doctor_id=doctor.id,
        start_date=today,
        end_date=today
    )

    return {
        "total": stats.total,
        "pending": stats.pending,
        "signed_in": stats.signed_in,
        "in_progress": stats.in_progress,
        "completed": stats.completed,
        "cancelled": stats.cancelled,
        "no_show": stats.no_show,
    }


@router.get("/statistics/trend", summary="获取预约趋势")
async def get_my_appointment_trend(
    days: int = Query(default=7, ge=1, le=30),
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """获取当前医生的预约趋势数据"""
    today = date.today()
    start_date = today - timedelta(days=days - 1)

    query = (
        select(
            func.date(Appointment.created_at).label('date'),
            func.count(Appointment.id).label('count')
        )
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .where(
            Schedule.doctor_id == doctor.id,
            func.date(Appointment.created_at) >= start_date,
            func.date(Appointment.created_at) <= today,
        )
        .group_by(func.date(Appointment.created_at))
        .order_by(func.date(Appointment.created_at))
    )

    result = await db.execute(query)
    rows = result.all()

    # 构建完整的日期序列（含零值日期）
    date_count_map = {str(row.date): row.count for row in rows}
    trend = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        date_str = d.isoformat()
        trend.append({
            "date": date_str,
            "count": date_count_map.get(date_str, 0),
        })

    return trend


@router.get("/statistics/status", summary="获取预约状态统计")
async def get_my_appointment_status_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """获取当前医生的预约状态分布"""
    query = (
        select(
            Appointment.status,
            func.count(Appointment.id).label('count')
        )
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .where(Schedule.doctor_id == doctor.id)
    )

    if start_date:
        query = query.where(func.date(Appointment.created_at) >= start_date)
    if end_date:
        query = query.where(func.date(Appointment.created_at) <= end_date)

    query = query.group_by(Appointment.status)
    result = await db.execute(query)
    rows = result.all()

    # 状态映射
    status_map = {
        0: "待支付",
        1: "已预约",
        2: "已签到",
        3: "候诊中",
        4: "就诊中",
        5: "已完成",
        6: "已取消",
        7: "已过期",
        8: "已爽约",
    }

    return [
        {
            "status": row.status,
            "name": status_map.get(row.status, "未知"),
            "count": row.count,
        }
        for row in rows
    ]
