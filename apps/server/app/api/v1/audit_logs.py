"""审计日志 API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.models.rule_set import AppointmentCheckin
from app.models.appointment import Appointment
from app.core.config import settings

router = APIRouter()


@router.get("/checkin-logs")
async def get_checkin_logs(
    appointment_id: Optional[str] = Query(None, description="预约ID"),
    patient_id: Optional[str] = Query(None, description="患者ID"),
    status: Optional[str] = Query(None, description="状态"),
    checkin_method: Optional[str] = Query(None, description="签到方式"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """查询签到审计日志"""

    # 构建查询
    query = select(AppointmentCheckin).options(
        selectinload(AppointmentCheckin.appointment)
    )

    # 筛选条件
    conditions = []

    if appointment_id:
        conditions.append(AppointmentCheckin.appointment_id == appointment_id)

    if status:
        conditions.append(AppointmentCheckin.status == status)

    if checkin_method:
        conditions.append(AppointmentCheckin.checkin_method == checkin_method)

    if start_time:
        conditions.append(AppointmentCheckin.checkin_time >= start_time)

    if end_time:
        conditions.append(AppointmentCheckin.checkin_time <= end_time)

    if patient_id:
        # 需要关联预约表查询
        query = query.join(Appointment, AppointmentCheckin.appointment_id == Appointment.id)
        conditions.append(Appointment.patient_id == patient_id)

    if conditions:
        query = query.where(and_(*conditions))

    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    query = query.order_by(desc(AppointmentCheckin.checkin_time))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    # 格式化返回（使用 camelCase 以便前端直接使用）
    items = []
    for log in logs:
        item = {
            "id": log.id,
            "appointmentId": log.appointment_id,
            "checkinTime": log.checkin_time.isoformat() if log.checkin_time else None,
            "checkinMethod": log.checkin_method,
            "deviceInfo": log.device_info,
            "locationInfo": log.location_info,
            "operatorId": log.operator_id,
            "operatorType": log.operator_type,
            "status": log.status,
            "failReason": log.fail_reason,
            "createdAt": log.created_at.isoformat() if log.created_at else None,
        }

        # 尝试从关联的预约获取患者信息
        if log.appointment:
            item["patientName"] = getattr(log.appointment, 'patient_name', None)
            item["patientPhone"] = getattr(log.appointment, 'patient_phone', None)
            item["doctorName"] = getattr(log.appointment, 'doctor_name', None)
            item["departmentName"] = getattr(log.appointment, 'department_name', None)

        items.append(item)

    return {
        "data": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/checkin-logs/statistics")
async def get_checkin_log_statistics(
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取签到审计日志统计"""

    # 构建查询
    query = select(
        AppointmentCheckin.status,
        func.count(AppointmentCheckin.id).label('count')
    )

    # 日期范围筛选
    conditions = []
    if start_date:
        conditions.append(AppointmentCheckin.checkin_time >= start_date)
    if end_date:
        conditions.append(AppointmentCheckin.checkin_time <= end_date)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.group_by(AppointmentCheckin.status)

    result = await db.execute(query)
    stats = result.all()

    return {
        "data": [
            {
                "status": row.status,
                "count": row.count
            }
            for row in stats
        ],
        "total": sum(row.count for row in stats)
    }
