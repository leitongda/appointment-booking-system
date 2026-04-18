"""预约状态流转相关端点"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.api.deps import get_current_user, get_current_admin, get_current_super_admin, check_store_access, require_permission
from app.modules.appointments.service import AppointmentService
from app.modules.appointments.common import CHECKIN_METHOD
from app.core.websocket import (
    notify_patient_signed_in,
    notify_doctor,
    WSMessageType,
)

router = APIRouter()


@router.put(
    "/{appointment_id}/sign-in",
    summary="签到",
    description="""
    患者签到，将预约状态从"已预约"变更为"已签到"，分配签到序号。

    **业务规则**：
    - 签到需在规则引擎允许的签到时间窗口内
    - 非管理员只能签到自己的预约（门店隔离）
    - 签到成功后通过 WebSocket 通知对应医生端

    **参数说明**：
    - appointment_id: 预约记录ID（路径参数）
    - checkin_method: 签到方式（可选，如 manual/qrcode/device）
    - device_info: 设备信息（可选）
    - location_info: 位置信息（可选）
    """,
)
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
            checkin_method=checkin_method or CHECKIN_METHOD["MANUAL"],
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


@router.put(
    "/{appointment_id}/cancel-sign-in",
    summary="取消签到",
    description="""
    取消签到，将预约状态从"已签到"恢复为"已预约"。

    **权限要求**：仅超级管理员可操作。

    **业务规则**：
    - 只有"已签到"状态的预约可以取消签到
    - 取消后释放对应的签到序号
    """,
)
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


@router.put(
    "/{appointment_id}/call",
    summary="叫号",
    description="""
    叫号，通知患者前来就诊，将预约状态变更为"就诊中"。

    **权限要求**：管理员权限（appointment:manage），受门店访问控制。

    **业务规则**：
    - 只有"已签到"状态的预约可以叫号
    - 叫号后通过 WebSocket 通知医生端
    - 管理员只能操作自己关联门店的预约
    """,
)
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


@router.put(
    "/{appointment_id}/complete",
    summary="完成就诊",
    description="""
    结束就诊，将预约状态变更为"已完成"。

    **权限要求**：管理员权限（appointment:manage），受门店访问控制。

    **业务规则**：
    - 只有"已签到"或"就诊中"状态的预约可以完成
    - 完成后通过 WebSocket 通知医生端
    - 记录完成时间（completeTime）
    """,
)
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


@router.put(
    "/{appointment_id}/pass",
    summary="过号",
    description="""
    过号处理，将预约状态变更为"已过号"。

    **权限要求**：管理员权限（appointment:manage），受门店访问控制。

    **业务规则**：
    - 只有"已签到"或"就诊中"状态的预约可以过号
    - 过号后患者可通过"重新叫号"恢复
    - 通过 WebSocket 通知医生端
    """,
)
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


@router.put(
    "/{appointment_id}/recall",
    summary="重新叫号",
    description="""
    对已过号的患者重新叫号，将状态恢复为"就诊中"。

    **权限要求**：管理员权限（appointment:manage），受门店访问控制。

    **业务规则**：
    - 只有"已过号"状态的预约可以重新叫号
    - 重新叫号后通过 WebSocket 通知医生端
    """,
)
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


@router.put(
    "/{appointment_id}/no-show",
    summary="标记爽约",
    description="""
    标记预约为爽约状态。

    **权限要求**：管理员权限（appointment:manage），受门店访问控制。

    **业务规则**：
    - 适用于预约了但未在规定时间内签到的患者
    - 标记爽约后释放对应排班的号源（booked_slots 减 1）
    - 通过 WebSocket 通知医生端
    """,
)
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
