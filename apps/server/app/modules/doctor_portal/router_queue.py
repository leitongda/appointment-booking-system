"""叫号管理相关端点"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from typing import Optional, List

from app.db.session import get_db
from app.api.deps import get_current_doctor_by_token
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.modules.appointments.service import AppointmentService
from app.modules.doctor_portal.schemas import QueuePatientResponse
from app.core.websocket import notify_doctor, WSMessageType

router = APIRouter()


async def _verify_appointment_ownership(
    appointment_id: str,
    doctor: Doctor,
    db: AsyncSession
) -> Appointment:
    """验证预约是否属于当前医生

    Args:
        appointment_id: 预约ID
        doctor: 当前医生
        db: 数据库会会

    Returns:
        预约对象

    Raises:
        HTTPException: 如果预约不存在或不属于当前医生
    """
    service = AppointmentService(db)
    appointment = await service.get_by_id(appointment_id)

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预约不存在"
        )

    # 验证预约属于当前医生
    if appointment.doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您无权操作此预约"
        )

    return appointment


@router.get("", response_model=List[QueuePatientResponse], summary="获取叫号队列")
async def get_my_queue(
    target_date: Optional[date] = None,
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """获取当前医生的签到队列

    返回已签到等待叫号的患者列表
    """
    service = AppointmentService(db)

    if not target_date:
        target_date = date.today()

    appointments = await service.get_checkin_queue(
        store_id=doctor.store_id,  # 门店隔离
        doctor_id=doctor.id,       # 只看自己的队列
        target_date=target_date
    )

    return [
        QueuePatientResponse(
            id=a.id,
            appointment_no=a.appointment_no,
            queue_number=a.queue_number,
            patient_name=a.patient_name,
            status=a.status,
            sign_in_time=a.sign_in_time,
            call_time=a.call_time,
        )
        for a in appointments
    ]


@router.get("/info", summary="获取队列信息")
async def get_my_queue_info(
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """获取当前医生的叫号队列统计信息"""
    service = AppointmentService(db)
    return await service.get_queue_info(doctor.id)


@router.put("/{appointment_id}/call", summary="叫号")
async def call_patient(
    appointment_id: str,
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """叫号 - 只能叫自己的患者"""
    # 验证预约属于当前医生
    await _verify_appointment_ownership(appointment_id, doctor, db)

    service = AppointmentService(db)

    try:
        appointment = await service.call_patient(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 发送 WebSocket 通知
    try:
        await notify_doctor(
            doctor_id=doctor.id,
            message_type=WSMessageType.PATIENT_CALLED,
            data={
                "appointment_id": appointment.id,
                "patient_name": appointment.patient_name,
                "queue_number": appointment.queue_number,
            }
        )
    except Exception:
        pass  # WebSocket 通知失败不影响业务

    return {"message": "已呼叫", "queue_number": appointment.queue_number}


@router.put("/{appointment_id}/complete", summary="完成就诊")
async def complete_consultation(
    appointment_id: str,
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """完成就诊 - 只能操作自己的患者"""
    # 验证预约属于当前医生
    await _verify_appointment_ownership(appointment_id, doctor, db)

    service = AppointmentService(db)
    appointment = await service.complete(appointment_id)

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预约不存在"
        )

    # 发送 WebSocket 通知
    try:
        await notify_doctor(
            doctor_id=doctor.id,
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
async def pass_patient(
    appointment_id: str,
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """过号 - 只能操作自己的患者"""
    # 验证预约属于当前医生
    await _verify_appointment_ownership(appointment_id, doctor, db)

    service = AppointmentService(db)

    try:
        appointment = await service.pass_number(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 发送 WebSocket 通知
    try:
        await notify_doctor(
            doctor_id=doctor.id,
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
async def recall_patient(
    appointment_id: str,
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """重新叫号 - 只能操作自己的患者"""
    # 验证预约属于当前医生
    await _verify_appointment_ownership(appointment_id, doctor, db)

    service = AppointmentService(db)

    try:
        appointment = await service.recall(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 发送 WebSocket 通知
    try:
        await notify_doctor(
            doctor_id=doctor.id,
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
async def mark_patient_no_show(
    appointment_id: str,
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """标记爽约 - 只能操作自己的患者"""
    # 验证预约属于当前医生
    await _verify_appointment_ownership(appointment_id, doctor, db)

    service = AppointmentService(db)

    try:
        appointment = await service.mark_no_show(appointment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 发送 WebSocket 通知
    try:
        await notify_doctor(
            doctor_id=doctor.id,
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
