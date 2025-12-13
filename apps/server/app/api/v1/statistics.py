"""数据统计 API"""
from datetime import date, datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.user import User
from app.models.doctor import Doctor
from app.models.department import Department
from app.schemas.response import ResponseModel

router = APIRouter()


@router.get("/overview", response_model=ResponseModel)
async def get_overview(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取概览数据"""
    today = date.today()
    
    # 今日预约数
    today_appointments = await db.scalar(
        select(func.count(Appointment.id)).where(
            func.date(Appointment.created_at) == today
        )
    )
    
    # 今日就诊数 - 通过 Schedule 获取 schedule_date
    today_visits = await db.scalar(
        select(func.count(Appointment.id))
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .where(
            and_(
                Schedule.schedule_date == today,
                Appointment.status == 5  # 已完成
            )
        )
    )
    
    # 总患者数
    total_patients = await db.scalar(
        select(func.count(User.id)).where(User.user_type == 'patient')
    )
    
    # 总医生数
    total_doctors = await db.scalar(
        select(func.count(Doctor.id)).where(Doctor.status == 1)
    )
    
    # 本月预约数
    first_day_of_month = today.replace(day=1)
    month_appointments = await db.scalar(
        select(func.count(Appointment.id)).where(
            func.date(Appointment.created_at) >= first_day_of_month
        )
    )
    
    # 本月收入（挂号费）- 通过 Schedule -> Doctor 获取 registration_fee
    month_revenue = await db.scalar(
        select(func.sum(Doctor.registration_fee))
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .where(
            and_(
                func.date(Appointment.created_at) >= first_day_of_month,
                Appointment.status.in_([2, 3, 5])  # 已签到、候诊中、已完成
            )
        )
    ) or 0
    
    return ResponseModel(data={
        "todayAppointments": today_appointments or 0,
        "todayVisits": today_visits or 0,
        "totalPatients": total_patients or 0,
        "totalDoctors": total_doctors or 0,
        "monthAppointments": month_appointments or 0,
        "monthRevenue": float(month_revenue),
    })


@router.get("/appointments/trend", response_model=ResponseModel)
async def get_appointment_trend(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取预约趋势数据"""
    today = date.today()
    start_date = today - timedelta(days=days - 1)
    
    # 查询每天的预约数
    result = await db.execute(
        select(
            func.date(Appointment.created_at).label('date'),
            func.count(Appointment.id).label('count')
        ).where(
            func.date(Appointment.created_at) >= start_date
        ).group_by(
            func.date(Appointment.created_at)
        ).order_by(
            func.date(Appointment.created_at)
        )
    )
    
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


@router.get("/appointments/status", response_model=ResponseModel)
async def get_appointment_status_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取预约状态统计"""
    query = select(
        Appointment.status,
        func.count(Appointment.id).label('count')
    )
    
    if start_date:
        query = query.where(func.date(Appointment.created_at) >= start_date)
    if end_date:
        query = query.where(func.date(Appointment.created_at) <= end_date)
    
    query = query.group_by(Appointment.status)
    
    result = await db.execute(query)
    
    status_map = {
        1: "待就诊",
        2: "已签到",
        3: "候诊中",
        4: "就诊中",
        5: "已完成",
        6: "已取消",
        7: "爽约",
    }
    
    data = [
        {"status": row.status, "name": status_map.get(row.status, "未知"), "count": row.count}
        for row in result.fetchall()
    ]
    
    return ResponseModel(data=data)


@router.get("/departments/ranking", response_model=ResponseModel)
async def get_department_ranking(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取科室预约排行"""
    # Appointment -> Doctor -> Department
    result = await db.execute(
        select(
            Department.id,
            Department.name,
            func.count(Appointment.id).label('count')
        ).join(
            Doctor, Doctor.department_id == Department.id
        ).join(
            Appointment, Appointment.doctor_id == Doctor.id
        ).group_by(
            Department.id, Department.name
        ).order_by(
            func.count(Appointment.id).desc()
        ).limit(limit)
    )
    
    data = [
        {"departmentId": row.id, "departmentName": row.name, "count": row.count}
        for row in result.fetchall()
    ]
    
    return ResponseModel(data=data)


@router.get("/doctors/ranking", response_model=ResponseModel)
async def get_doctor_ranking(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取医生预约排行"""
    result = await db.execute(
        select(
            Doctor.id,
            Doctor.name,
            Doctor.title,
            Department.name.label('department_name'),
            func.count(Appointment.id).label('count')
        ).join(
            Appointment, Appointment.doctor_id == Doctor.id
        ).join(
            Department, Doctor.department_id == Department.id
        ).group_by(
            Doctor.id, Doctor.name, Doctor.title, Department.name
        ).order_by(
            func.count(Appointment.id).desc()
        ).limit(limit)
    )
    
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


@router.get("/time-slots/distribution", response_model=ResponseModel)
async def get_time_slot_distribution(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取时段分布统计"""
    # 通过 Schedule 获取 time_slot
    result = await db.execute(
        select(
            Schedule.time_slot,
            func.count(Appointment.id).label('count')
        )
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .group_by(Schedule.time_slot)
    )
    
    slot_map = {
        "AM": "上午",
        "PM": "下午",
        "NIGHT": "晚上",
    }
    
    data = [
        {"timeSlot": row.time_slot, "name": slot_map.get(row.time_slot, row.time_slot), "count": row.count}
        for row in result.fetchall()
    ]
    
    return ResponseModel(data=data)


@router.get("/weekday/distribution", response_model=ResponseModel)
async def get_weekday_distribution(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取星期分布统计"""
    # 使用 extract 获取星期几（0=周日，1=周一...6=周六）- 通过 Schedule 获取 schedule_date
    result = await db.execute(
        select(
            func.extract('dow', Schedule.schedule_date).label('weekday'),
            func.count(Appointment.id).label('count')
        )
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .group_by(
            func.extract('dow', Schedule.schedule_date)
        ).order_by(
            func.extract('dow', Schedule.schedule_date)
        )
    )
    
    weekday_names = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
    
    data = [
        {"weekday": int(row.weekday), "name": weekday_names[int(row.weekday)], "count": row.count}
        for row in result.fetchall()
    ]
    
    return ResponseModel(data=data)


@router.get("/revenue/trend", response_model=ResponseModel)
async def get_revenue_trend(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取收入趋势"""
    today = date.today()
    start_date = today - timedelta(days=days - 1)
    
    # 通过 Schedule -> Doctor 获取 registration_fee
    result = await db.execute(
        select(
            func.date(Appointment.created_at).label('date'),
            func.sum(Doctor.registration_fee).label('revenue')
        )
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .where(
            and_(
                func.date(Appointment.created_at) >= start_date,
                Appointment.status.in_([2, 3, 5])  # 有效预约
            )
        ).group_by(
            func.date(Appointment.created_at)
        ).order_by(
            func.date(Appointment.created_at)
        )
    )
    
    data = {str(row.date): float(row.revenue or 0) for row in result.fetchall()}
    
    trend = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        trend.append({
            "date": str(d),
            "revenue": data.get(str(d), 0)
        })
    
    return ResponseModel(data=trend)

