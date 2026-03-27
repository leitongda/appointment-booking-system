"""预约 API - 聚合路由"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import date, datetime

from app.db.session import get_db
from app.api.deps import get_current_user, get_current_user_or_admin, get_store_filter, get_current_admin
from app.schemas.appointment import AppointmentCreate, AppointmentResponse, AppointmentCancelRequest
from app.schemas.response import PageResponse, ErrorResponse
from app.modules.appointments.service import AppointmentService
from app.core.config import settings


# 常规分页上限（超过此值需要管理员权限+日期范围）
PAGE_SIZE_STANDARD_LIMIT = 100

router = APIRouter()

# ==================== 根级别操作（保持在主路由器中以避免路径冲突） ====================

@router.get("", response_model=PageResponse[AppointmentResponse], summary="获取预约列表")
async def get_appointments(
    status_filter: Optional[int] = Query(None, alias="status"),
    patient_id: Optional[str] = None,
    store_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    keyword: Optional[str] = None,
    doctor_id: Optional[str] = None,
    department_id: Optional[str] = None,
    created_start: Optional[datetime] = None,
    created_end: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.APPOINTMENTS_MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin)
):
    """获取预约列表

    分页规则：
    - 默认 page_size=10
    - 常规上限为 100
    - 当 page_size > 100 时，需要管理员权限且必须提供 start_date 和 end_date
    """
    # 分页参数校验：超过100需要管理员权限+日期范围
    if page_size > PAGE_SIZE_STANDARD_LIMIT:
        is_admin = current_user.get("is_admin", False)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "PAGE_SIZE_REQUIRES_ADMIN",
                    "message": f"page_size > {PAGE_SIZE_STANDARD_LIMIT} 需要管理员权限",
                    "hint": f"当前 page_size={page_size}，普通用户上限为 {PAGE_SIZE_STANDARD_LIMIT}"
                }
            )
        if not start_date or not end_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "PAGE_SIZE_REQUIRES_DATE_RANGE",
                    "message": f"page_size > {PAGE_SIZE_STANDARD_LIMIT} 必须提供 start_date 和 end_date",
                    "hint": "请提供日期范围以限制查询数据量"
                }
            )

    service = AppointmentService(db)
    user_id = None if current_user.get("is_admin") else current_user["id"]

    if current_user.get("is_admin"):
        store_filter = get_store_filter(current_user)
        if store_filter:
            store_id = store_filter

    appointments, total = await service.get_list(
        user_id=user_id,
        store_id=store_id,
        status=status_filter,
        patient_id=patient_id,
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
        doctor_id=doctor_id,
        department_id=department_id,
        created_start=created_start,
        created_end=created_end,
        page=page,
        page_size=page_size
    )

    result = []
    for a in appointments:
        result.append(AppointmentResponse(
            id=a.id,
            appointment_no=a.appointment_no,
            user_id=a.user_id,
            patient_id=a.patient_id,
            patient_name=a.patient_name,
            patient_phone=a.patient_phone,
            doctor_id=a.doctor_id,
            doctor_name=a.doctor_name,
            doctor_title=a.doctor_title,
            department_name=a.department_name,
            schedule_id=a.schedule_id,
            schedule_date=a.schedule.schedule_date if a.schedule else None,
            time_slot=a.schedule.time_slot if a.schedule else None,
            start_time=a.schedule.start_time if a.schedule else None,
            end_time=a.schedule.end_time if a.schedule else None,
            queue_number=a.queue_number,
            status=a.status,
            sign_in_time=a.sign_in_time,
            call_time=a.call_time,
            complete_time=a.complete_time,
            cancel_time=a.cancel_time,
            cancel_reason=a.cancel_reason,
            symptom_description=a.symptom_description,
            created_at=a.created_at
        ))

    return PageResponse(data=result, total=total, page=page, page_size=page_size)


@router.post(
    "",
    response_model=AppointmentResponse,
    summary="创建预约",
    responses={
        400: {"model": ErrorResponse, "description": "预约失败"},
        404: {"model": ErrorResponse, "description": "排班不存在"},
    }
)
async def create_appointment(
    data: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin)
):
    """创建预约"""
    service = AppointmentService(db)

    try:
        appointment = await service.create(current_user["id"], data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 发送 WebSocket 通知
    if appointment.doctor_id:
        try:
            from app.core.websocket import notify_new_appointment
            await notify_new_appointment(
                doctor_id=appointment.doctor_id,
                appointment_data={
                    "appointment_id": appointment.id,
                    "patient_name": appointment.patient_name,
                    "queue_number": appointment.queue_number,
                    "schedule_date": appointment.schedule.schedule_date.isoformat() if appointment.schedule else None,
                    "time_slot": appointment.schedule.time_slot if appointment.schedule else None,
                }
            )
        except Exception:
            pass

    return AppointmentResponse(
        id=appointment.id,
        appointment_no=appointment.appointment_no,
        user_id=appointment.user_id,
        patient_id=appointment.patient_id,
        patient_name=appointment.patient_name,
        patient_phone=appointment.patient_phone,
        doctor_id=appointment.doctor_id,
        doctor_name=appointment.doctor_name,
        doctor_title=appointment.doctor_title,
        department_name=appointment.department_name,
        schedule_id=appointment.schedule_id,
        schedule_date=appointment.schedule.schedule_date if appointment.schedule else None,
        time_slot=appointment.schedule.time_slot if appointment.schedule else None,
        start_time=appointment.schedule.start_time if appointment.schedule else None,
        end_time=appointment.schedule.end_time if appointment.schedule else None,
        queue_number=appointment.queue_number,
        status=appointment.status,
        sign_in_time=appointment.sign_in_time,
        symptom_description=appointment.symptom_description,
        created_at=appointment.created_at
    )


@router.put(
    "/{appointment_id}/cancel",
    summary="取消预约",
    responses={
        400: {"model": ErrorResponse, "description": "取消失败"},
        404: {"model": ErrorResponse, "description": "预约不存在"},
    }
)
async def cancel_appointment(
    appointment_id: str,
    data: AppointmentCancelRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin)
):
    """取消预约"""
    service = AppointmentService(db)
    reason = data.reason if data else None
    is_admin = current_user.get("is_admin", False)

    try:
        appointment = await service.cancel(appointment_id, current_user["id"], reason, is_admin)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在")

    return {"message": "取消成功"}


# ==================== 聚合子模块路由 ====================

from .router_query import router as query_router
from .router_flow import router as flow_router

# 子路由器使用非空路径前缀
router.include_router(query_router, prefix="/query", tags=["预约查询"])
router.include_router(flow_router, tags=["预约状态流转"])
