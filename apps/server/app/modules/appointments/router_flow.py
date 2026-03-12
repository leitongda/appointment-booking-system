"""预约状态流转相关端点"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.api.deps import get_current_user, get_current_admin, get_current_super_admin, check_store_access, require_permission
from app.modules.appointments.service import AppointmentService
from app.core.websocket import (
    notify_patient_signed_in,
    notify_doctor,
    WSMessageType,
)

router = APIRouter()


@router.put("/{appointment_id}/sign-in", summary="签到")
async def sign_in_appointment(
    appointment_id: str,
    checkin_method: Optional[str] = Body(None, embed=True),
    device_info: Optional[str] = Body(None, embed=True),
    location_info: Optional[str] = Body(None, embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """签到

    权限验证：非管理员只能签到自己的预约（门店隔离）
    """
    service = AppointmentService(db)

    # 提取设备信息（从请求头）
    if not device_info:
        device_info = current_user.get("user_agent")

    try:
        appointment = await service.sign_in(
            appointment_id=appointment_id,
            user_id=current_user.get("id"),
            is_admin=current_user.get("is_admin", False),
            checkin_method=checkin_method or 'MANUAL',
            device_info=device_info,
            location_info=location_info,
            operator_id=current_user.get("id"),
            operator_type='ADMIN' if current_user.get("is_admin") else 'USER'
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在，请检查后重试")

    # 发送 WebSocket 通知给医生
    if appointment.doctor_id:
        try:
            await notify_patient_signed_in(
                doctor_id=appointment.doctor_id,
                appointment_data={
                    "appointment_id": appointment.id,
                    "patient_name": appointment.patient_name,
                    "queue_number": appointment.queue_number,
                    "time_slot": appointment.time_slot,
                    "sign_in_time": appointment.sign_in_time.isoformat() if appointment.sign_in_time else None,
                }
            )
        except Exception:
            pass  # WebSocket 通知失败不影响业务

    return {"message": "签到成功", "queueNumber": appointment.queue_number}


@router.put("/{appointment_id}/cancel-sign-in", summary="取消签到")
async def cancel_sign_in_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """取消签到（仅超级管理员）

    将状态从"已签到"恢复为"已预约"
    """
    service = AppointmentService(db)

    try:
        appointment = await service.cancel_sign_in(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在，请检查后重试")

    return {"message": "取消签到成功"}


@router.put("/{appointment_id}/call", summary="叫号")
async def call_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("appointment:manage"))
):
    """叫号（需要管理员权限）"""
    service = AppointmentService(db)

    # 先获取预约信息，检查门店访问权限
    appointment = await service.get_by_id(appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在，请检查后重试")

    # 检查门店访问权限
    if appointment.schedule and appointment.schedule.store_id:
        if not check_store_access(current_admin, appointment.schedule.store_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权操作此门店的预约")

    try:
        appointment = await service.call_patient(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 发送 WebSocket 通知
    if appointment.doctor_id:
        try:
            await notify_doctor(
                doctor_id=appointment.doctor_id,
                message_type=WSMessageType.PATIENT_CALLED,
                data={
                    "appointment_id": appointment.id,
                    "patient_name": appointment.patient_name,
                    "queue_number": appointment.queue_number,
                }
            )
        except Exception:
            pass  # WebSocket 通知失败不影响业务

    return {"message": "已呼叫"}


@router.put("/{appointment_id}/complete", summary="完成就诊")
async def complete_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("appointment:manage"))
):
    """完成就诊（需要管理员权限）"""
    service = AppointmentService(db)

    # 先获取预约信息，检查门店访问权限
    appointment = await service.get_by_id(appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在，请检查后重试")

    # 检查门店访问权限
    if appointment.schedule and appointment.schedule.store_id:
        if not check_store_access(current_admin, appointment.schedule.store_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权操作此门店的预约")

    appointment = await service.complete(appointment_id)

    # 发送 WebSocket 通知
    if appointment.doctor_id:
        try:
            await notify_doctor(
                doctor_id=appointment.doctor_id,
                message_type=WSMessageType.PATIENT_COMPLETED,
                data={
                    "appointment_id": appointment.id,
                    "patient_name": appointment.patient_name,
                    "queue_number": appointment.queue_number,
                }
            )
        except Exception:
            pass

    return {"message": "就诊完成"}


@router.put("/{appointment_id}/pass", summary="过号")
async def pass_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("appointment:manage"))
):
    """过号（需要管理员权限）"""
    service = AppointmentService(db)

    # 先获取预约信息，检查门店访问权限
    appointment = await service.get_by_id(appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在，请检查后重试")

    # 检查门店访问权限
    if appointment.schedule and appointment.schedule.store_id:
        if not check_store_access(current_admin, appointment.schedule.store_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权操作此门店的预约")

    try:
        appointment = await service.pass_number(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 发送 WebSocket 通知
    if appointment.doctor_id:
        try:
            await notify_doctor(
                doctor_id=appointment.doctor_id,
                message_type=WSMessageType.PATIENT_PASSED,
                data={
                    "appointment_id": appointment.id,
                    "patient_name": appointment.patient_name,
                    "queue_number": appointment.queue_number,
                }
            )
        except Exception:
            pass

    return {"message": "已过号"}


@router.put("/{appointment_id}/recall", summary="重新叫号")
async def recall_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("appointment:manage"))
):
    """重新叫号（需要管理员权限）"""
    service = AppointmentService(db)

    # 先获取预约信息，检查门店访问权限
    appointment = await service.get_by_id(appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在，请检查后重试")

    # 检查门店访问权限
    if appointment.schedule and appointment.schedule.store_id:
        if not check_store_access(current_admin, appointment.schedule.store_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权操作此门店的预约")

    try:
        appointment = await service.recall(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 发送 WebSocket 通知
    if appointment.doctor_id:
        try:
            await notify_doctor(
                doctor_id=appointment.doctor_id,
                message_type=WSMessageType.PATIENT_RECALLED,
                data={
                    "appointment_id": appointment.id,
                    "patient_name": appointment.patient_name,
                    "queue_number": appointment.queue_number,
                }
            )
        except Exception:
            pass

    return {"message": "已重新呼叫"}


@router.put("/{appointment_id}/no-show", summary="标记爽约")
async def mark_no_show(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("appointment:manage"))
):
    """标记爽约（需要管理员权限）"""
    service = AppointmentService(db)

    # 先获取预约信息，检查门店访问权限
    appointment = await service.get_by_id(appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在，请检查后重试")

    # 检查门店访问权限
    if appointment.schedule and appointment.schedule.store_id:
        if not check_store_access(current_admin, appointment.schedule.store_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权操作此门店的预约")

    try:
        appointment = await service.mark_no_show(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 发送 WebSocket 通知
    if appointment.doctor_id:
        try:
            await notify_doctor(
                doctor_id=appointment.doctor_id,
                message_type=WSMessageType.PATIENT_NO_SHOW,
                data={
                    "appointment_id": appointment.id,
                    "patient_name": appointment.patient_name,
                    "queue_number": appointment.queue_number,
                }
            )
        except Exception:
            pass

    return {"message": "已标记爽约"}
