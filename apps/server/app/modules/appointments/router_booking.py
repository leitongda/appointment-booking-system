"""预约创建和取消相关端点"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user_or_admin, require_tenant_active_for_write
from app.schemas.appointment import (
    AppointmentCancelRequest,
    AppointmentCreate,
    AppointmentPendingPaymentResponse,
    AppointmentResponse,
)
from app.schemas.response import ErrorResponse
from app.modules.appointments.service import AppointmentService

router = APIRouter()


def _serialize_created_appointment(result):
    if isinstance(result, dict):
        return AppointmentPendingPaymentResponse.from_result(result)
    return AppointmentResponse.from_appointment(result)


@router.post(
    "",
    response_model=AppointmentResponse | AppointmentPendingPaymentResponse,
    summary="创建预约",
    responses={
        400: {"model": ErrorResponse, "description": "预约失败（号源已满/重复预约/黑名单等）"},
        401: {"model": ErrorResponse, "description": "未登录或 Token 过期"},
        404: {"model": ErrorResponse, "description": "排班不存在"},
    }
)
async def create_appointment(
    data: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
    _tenant_guard: None = Depends(require_tenant_active_for_write),
):
    """创建预约"""
    service = AppointmentService(db)

    try:
        result = await service.create(current_user["id"], data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    appointment = result["appointment"] if isinstance(result, dict) else result

    # 发送 WebSocket 通知给医生（新预约）
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
            pass  # WebSocket 通知失败不影响业务

    return _serialize_created_appointment(result)


@router.put(
    "/{appointment_id}/cancel",
    summary="取消预约",
    responses={
        400: {"model": ErrorResponse, "description": "取消失败（已超过可取消时间/状态不允许取消）"},
        404: {"model": ErrorResponse, "description": "预约不存在"},
    }
)
async def cancel_appointment(
    appointment_id: str,
    data: AppointmentCancelRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
    _tenant_guard: None = Depends(require_tenant_active_for_write),
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在，请检查后重试")

    return {"message": "取消成功"}
