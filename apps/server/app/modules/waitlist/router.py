"""候补队列路由"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_admin,
    get_current_user,
    require_tenant_active_for_write,
    resolve_actor_tenant_anchor,
)
from app.common.deps import require_permission
from app.core.config import settings
from app.db.session import get_db
from app.modules.waitlist.service import WaitlistService

router = APIRouter()


@router.post("", summary="加入候补队列")
async def join_waitlist(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _tenant_guard: None = Depends(require_tenant_active_for_write),
):
    """用户加入候补队列"""
    user_id = current_user.get("user_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
        )

    schedule_id = data.get("schedule_id")
    patient_id = data.get("patient_id")
    symptom_description = data.get("symptom_description")

    if not schedule_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少排班ID",
        )

    service = WaitlistService(db)
    try:
        entry = await service.add_to_waitlist(
            user_id=user_id,
            patient_id=patient_id or user_id,
            schedule_id=schedule_id,
            symptom_description=symptom_description,
            operator_id=user_id,
            tenant_id=resolve_actor_tenant_anchor(current_user),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return {
        "id": entry.id,
        "user_id": entry.user_id,
        "patient_id": entry.patient_id,
        "schedule_id": entry.schedule_id,
        "status": entry.status,
        "position": entry.position,
        "priority": entry.priority,
        "symptom_description": entry.symptom_description,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


@router.put("/{entry_id}/cancel", summary="取消候补")
async def cancel_waitlist(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """取消候补"""
    user_id = current_user.get("user_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
        )

    service = WaitlistService(db)
    try:
        entry = await service.cancel_waitlist(
            entry_id=entry_id,
            user_id=user_id,
            is_admin=False,
            operator_id=user_id,
            tenant_id=resolve_actor_tenant_anchor(current_user),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="候补记录不存在或无权操作",
        )

    return {
        "id": entry.id,
        "status": entry.status,
        "cancelled_at": entry.cancelled_at.isoformat() if entry.cancelled_at else None,
    }


@router.get("/my", summary="获取我的候补列表")
async def get_my_waitlist(
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取当前用户的候补列表"""
    user_id = current_user.get("user_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
        )

    from sqlalchemy import and_, func, select

    from app.middleware.tenant_context import get_current_tenant_id
    from app.models.department import Department
    from app.models.doctor import Doctor
    from app.models.schedule import Schedule
    from app.models.store import Store
    from app.models.waitlist import WaitlistEntry

    # 构建查询
    conditions = [WaitlistEntry.user_id == user_id]
    tenant_id = resolve_actor_tenant_anchor(current_user)
    if tenant_id:
        conditions.append(WaitlistEntry.tenant_id == tenant_id)
    if status_filter:
        conditions.append(WaitlistEntry.status == status_filter)

    where_clause = and_(*conditions)

    # 统计总数
    count_stmt = select(func.count(WaitlistEntry.id)).where(where_clause)
    total = await db.scalar(count_stmt) or 0

    # 查询列表（关联排班信息）
    stmt = (
        select(WaitlistEntry, Schedule, Doctor, Department, Store)
        .join(Schedule, WaitlistEntry.schedule_id == Schedule.id)
        .outerjoin(Doctor, Schedule.doctor_id == Doctor.id)
        .outerjoin(Department, Doctor.department_id == Department.id)
        .outerjoin(Store, Schedule.store_id == Store.id)
        .where(where_clause)
        .order_by(WaitlistEntry.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for entry, schedule, doctor, department, store in rows:
        items.append({
            "id": entry.id,
            "user_id": entry.user_id,
            "patient_id": entry.patient_id,
            "schedule_id": entry.schedule_id,
            "status": entry.status,
            "position": entry.position,
            "priority": entry.priority,
            "symptom_description": entry.symptom_description,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            "promoted_at": entry.promoted_at.isoformat() if entry.promoted_at else None,
            "cancelled_at": entry.cancelled_at.isoformat() if entry.cancelled_at else None,
            "schedule": {
                "id": schedule.id,
                "schedule_date": schedule.schedule_date.isoformat() if schedule.schedule_date else None,
                "time_slot": schedule.time_slot,
                "start_time": schedule.start_time.strftime("%H:%M") if schedule.start_time else None,
                "end_time": schedule.end_time.strftime("%H:%M") if schedule.end_time else None,
                "total_slots": schedule.total_slots,
                "booked_slots": schedule.booked_slots,
                "doctor_name": doctor.name if doctor else None,
                "doctor_title": doctor.title if doctor else None,
                "department_name": department.name if department else None,
                "store_name": store.name if store else None,
            } if schedule else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/position", summary="获取排队位置")
async def get_waitlist_position(
    schedule_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取用户在指定排班候补队列中的位置"""
    user_id = current_user.get("user_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
        )

    service = WaitlistService(db)
    position = await service.get_waitlist_position(
        schedule_id=schedule_id,
        user_id=user_id,
    )

    return {"position": position}


# ==================== 管理端接口 ====================


@router.get("/stats", summary="获取候补统计")
async def get_waitlist_stats(
    store_id: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("waitlist:read")),
):
    """管理端：候补队列统计（总数 / 等待中 / 已递补 / 已取消）"""
    from sqlalchemy import func, select

    from app.models.schedule import Schedule
    from app.models.waitlist import WaitlistEntry

    stmt = select(
        WaitlistEntry.status,
        func.count(WaitlistEntry.id),
    )
    if store_id:
        # WaitlistEntry 无 store_id 列，按排班关联过滤
        stmt = stmt.join(Schedule, WaitlistEntry.schedule_id == Schedule.id)
    stmt = stmt.group_by(WaitlistEntry.status)

    tenant_id = resolve_actor_tenant_anchor(current_admin)
    if tenant_id:
        stmt = stmt.where(WaitlistEntry.tenant_id == tenant_id)
    if store_id:
        stmt = stmt.where(Schedule.store_id == store_id)
    if start_date:
        stmt = stmt.where(WaitlistEntry.created_at >= start_date)
    if end_date:
        stmt = stmt.where(WaitlistEntry.created_at <= end_date)

    rows = (await db.execute(stmt)).all()
    counts = {row[0]: row[1] for row in rows}
    total = sum(counts.values())
    return {
        "total": total,
        "waiting": counts.get("WAITING", 0),
        "promoted": counts.get("PROMOTED", 0),
        "cancelled": counts.get("CANCELLED", 0),
    }


@router.get("", summary="管理端：候补列表")
async def admin_list_waitlist(
    store_id: str | None = Query(None),
    department_id: str | None = Query(None),
    doctor_id: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("waitlist:read")),
):
    """管理端：候补列表（支持门店/科室/医生/状态/日期/关键词筛选 + 分页）"""
    from sqlalchemy import or_, select

    from app.middleware.tenant_context import get_current_tenant_id
    from app.models.doctor import Doctor
    from app.models.user import Patient
    from app.models.schedule import Schedule
    from app.models.waitlist import WaitlistEntry

    stmt = (
        select(WaitlistEntry, Schedule, Doctor, Patient)
        .join(Schedule, WaitlistEntry.schedule_id == Schedule.id)
        .outerjoin(Doctor, Schedule.doctor_id == Doctor.id)
        .outerjoin(Patient, WaitlistEntry.patient_id == Patient.id)
    )

    tenant_id = resolve_actor_tenant_anchor(current_admin)
    if tenant_id:
        stmt = stmt.where(WaitlistEntry.tenant_id == tenant_id)
    if store_id:
        stmt = stmt.where(Schedule.store_id == store_id)
    if department_id:
        stmt = stmt.where(Doctor.department_id == department_id)
    if doctor_id:
        stmt = stmt.where(Schedule.doctor_id == doctor_id)
    if status_filter:
        stmt = stmt.where(WaitlistEntry.status == status_filter)
    if start_date:
        stmt = stmt.where(WaitlistEntry.created_at >= start_date)
    if end_date:
        stmt = stmt.where(WaitlistEntry.created_at <= end_date)
    if keyword:
        # LIKE 通配符转义，避免用户输入的 % / _ 改变匹配语义
        escaped_keyword = (
            keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        pattern = f"%{escaped_keyword}%"
        stmt = stmt.where(
            or_(
                Patient.name.ilike(pattern, escape="\\"),
                Patient.phone.ilike(pattern, escape="\\"),
            )
        )

    # 总数：对已带租户/筛选条件的子查询计数，避免引用原表导致跨租户计数失真
    from sqlalchemy import func as _func
    count_subq = stmt.order_by(None).subquery()
    total = (
        await db.execute(select(_func.count()).select_from(count_subq))
    ).scalar_one()

    # 分页
    stmt = stmt.order_by(WaitlistEntry.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).all()

    data = []
    for entry, schedule, doctor, patient in rows:
        data.append({
            "id": entry.id,
            "user_id": entry.user_id,
            "patient_id": entry.patient_id,
            "patient_name": patient.name if patient else None,
            "patient_phone": patient.phone if patient else None,
            "schedule_id": entry.schedule_id,
            "status": entry.status,
            "position": entry.position,
            "priority": entry.priority,
            "symptom_description": entry.symptom_description,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            "promoted_at": entry.promoted_at.isoformat() if entry.promoted_at else None,
            "cancelled_at": entry.cancelled_at.isoformat() if entry.cancelled_at else None,
            "schedule_date": schedule.schedule_date.isoformat() if schedule and schedule.schedule_date else None,
            "time_slot": schedule.time_slot if schedule else None,
            "doctor_name": doctor.name if doctor else None,
            "department_name": None,  # 可按需 join Department 补全
        })

    return {
        "data": data,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/{entry_id}/promote", summary="管理端：手动递补")
async def admin_promote_waitlist(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("waitlist:promote")),
):
    """管理端：手动将指定候补用户递补为正式预约"""
    from sqlalchemy import select

    from app.middleware.tenant_context import get_current_tenant_id
    from app.models.waitlist import WaitlistEntry

    # 取候补记录（校验存在 + 租户）
    stmt = select(WaitlistEntry).where(WaitlistEntry.id == entry_id)
    tenant_id = resolve_actor_tenant_anchor(current_admin)
    if tenant_id:
        stmt = stmt.where(WaitlistEntry.tenant_id == tenant_id)
    entry = (await db.execute(stmt)).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="候补记录不存在")

    if entry.status != "WAITING":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅等待中的候补可递补")

    service = WaitlistService(db)
    appointment = await service.promote_next(
        schedule_id=entry.schedule_id,
        operator_id=current_admin.get("id"),
        tenant_id=tenant_id,
    )
    if not appointment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="递补失败，可能已无可用号源")

    return {
        "id": entry.id,
        "status": "PROMOTED",
        "appointment_id": appointment.id,
        "promoted_at": entry.promoted_at.isoformat() if entry.promoted_at else None,
    }


@router.post("/{entry_id}/cancel", summary="管理端：取消候补")
async def admin_cancel_waitlist(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("waitlist:cancel")),
):
    """管理端：取消指定候补记录（不校验 user_id 归属，管理员可操作任意记录）"""
    service = WaitlistService(db)
    try:
        entry = await service.cancel_waitlist(
            entry_id=entry_id,
            user_id=None,  # 管理员操作不限定归属
            is_admin=True,
            operator_id=current_admin.get("id"),
            tenant_id=resolve_actor_tenant_anchor(current_admin),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="候补记录不存在")

    return {
        "id": entry.id,
        "status": entry.status,
        "cancelled_at": entry.cancelled_at.isoformat() if entry.cancelled_at else None,
    }


@router.get("/{entry_id}", summary="获取候补详情")
async def get_waitlist_detail(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取候补详情"""
    user_id = current_user.get("user_id") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
        )

    from sqlalchemy import select

    from app.middleware.tenant_context import get_current_tenant_id
    from app.models.department import Department
    from app.models.doctor import Doctor
    from app.models.schedule import Schedule
    from app.models.store import Store
    from app.models.waitlist import WaitlistEntry

    # 查询详情
    stmt = (
        select(WaitlistEntry, Schedule, Doctor, Department, Store)
        .join(Schedule, WaitlistEntry.schedule_id == Schedule.id)
        .outerjoin(Doctor, Schedule.doctor_id == Doctor.id)
        .outerjoin(Department, Doctor.department_id == Department.id)
        .outerjoin(Store, Schedule.store_id == Store.id)
        .where(WaitlistEntry.id == entry_id)
    )

    # 租户过滤
    tenant_id = resolve_actor_tenant_anchor(current_user)
    if tenant_id:
        stmt = stmt.where(WaitlistEntry.tenant_id == tenant_id)

    result = await db.execute(stmt)
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="候补记录不存在",
        )

    entry, schedule, doctor, department, store = row

    # 权限检查：只能查看自己的候补
    if entry.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看此候补记录",
        )

    return {
        "id": entry.id,
        "user_id": entry.user_id,
        "patient_id": entry.patient_id,
        "schedule_id": entry.schedule_id,
        "status": entry.status,
        "position": entry.position,
        "priority": entry.priority,
        "symptom_description": entry.symptom_description,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "promoted_at": entry.promoted_at.isoformat() if entry.promoted_at else None,
        "cancelled_at": entry.cancelled_at.isoformat() if entry.cancelled_at else None,
        "schedule": {
            "id": schedule.id,
            "schedule_date": schedule.schedule_date.isoformat() if schedule.schedule_date else None,
            "time_slot": schedule.time_slot,
            "start_time": schedule.start_time.strftime("%H:%M") if schedule.start_time else None,
            "end_time": schedule.end_time.strftime("%H:%M") if schedule.end_time else None,
            "total_slots": schedule.total_slots,
            "booked_slots": schedule.booked_slots,
            "doctor_name": doctor.name if doctor else None,
            "doctor_title": doctor.title if doctor else None,
            "department_name": department.name if department else None,
            "store_name": store.name if store else None,
        } if schedule else None,
    }
