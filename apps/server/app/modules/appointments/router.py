"""预约 API - 聚合路由"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user_or_admin
from app.schemas.appointment import AppointmentCreate, AppointmentResponse, AppointmentCancelRequest
from app.schemas.response import ErrorResponse
from app.modules.appointments.service import AppointmentService


router = APIRouter()

# ==================== 根级别操作（保持在主路由器中以避免路径冲突） ====================


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
