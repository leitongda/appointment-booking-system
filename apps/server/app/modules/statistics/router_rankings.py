"""数据统计 - 科室、医生、门店排行"""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_store_filter, get_tenant_filter
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.store import Store
from app.modules.statistics.helpers import (
    _build_store_filter_condition,
    _build_tenant_condition,
)
from app.schemas.response import ResponseModel

router = APIRouter()


@router.get("/departments/ranking", response_model=ResponseModel, summary="获取科室预约排行")
async def get_department_ranking(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    tenant_id: str | None = Depends(get_tenant_filter),
):
    """获取科室预约排行"""
    # 获取门店过滤条件
    store_filter = get_store_filter(current_admin)
    store_condition = _build_store_filter_condition(store_filter)
    tenant_condition = _build_tenant_condition(Doctor, tenant_id)

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
    if tenant_condition is not None:
        query = query.where(tenant_condition)

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
    current_admin = Depends(get_current_admin),
    tenant_id: str | None = Depends(get_tenant_filter),
):
    """获取医生预约排行"""
    # 获取门店过滤条件
    store_filter = get_store_filter(current_admin)
    store_condition = _build_store_filter_condition(store_filter)
    tenant_condition = _build_tenant_condition(Doctor, tenant_id)

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
    if tenant_condition is not None:
        query = query.where(tenant_condition)

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


@router.get("/stores/ranking", response_model=ResponseModel, summary="获取门店预约排行")
async def get_store_ranking(
    limit: int = Query(default=10, ge=1, le=50),
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    tenant_id: str | None = Depends(get_tenant_filter),
):
    """获取门店预约排行（只有超管可以看到所有门店排行）"""
    # 获取门店过滤条件
    store_filter = get_store_filter(current_admin)
    store_condition = _build_store_filter_condition(store_filter)
    tenant_condition = _build_tenant_condition(Store, tenant_id)

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
    if tenant_condition is not None:
        conditions.append(tenant_condition)

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
