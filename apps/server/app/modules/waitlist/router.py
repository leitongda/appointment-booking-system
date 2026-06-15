"""候补队列路由"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.modules.waitlist.service import WaitlistService

router = APIRouter()


@router.post("", summary="加入候补队列")
async def join_waitlist(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
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
    tenant_id = get_current_tenant_id()
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
    tenant_id = get_current_tenant_id()
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
