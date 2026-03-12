"""患者相关端点"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.db.session import get_db
from app.api.deps import get_current_doctor_by_token
from app.models.doctor import Doctor
from app.modules.appointments.service import AppointmentService
from app.models.medical_record import MedicalRecord
from app.modules.doctor_portal.schemas import (
    PatientHistoryResponse,
    FollowUpBookingRequest,
)

router = APIRouter()


@router.get("/{patient_id}/appointments", summary="获取患者历史")
async def get_patient_history(
    patient_id: str,
    status: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """获取患者在当前医生处的历史就诊记录

    只返回该患者在当前医生处的历史预约，用于医生查看患者就诊历史。
    """
    service = AppointmentService(db)

    # 只查询该患者在当前医生处的预约
    appointments, total = await service.get_list(
        patient_id=patient_id,
        doctor_id=doctor.id,
        status=status,
        page=page,
        page_size=page_size
    )

    # 查询病历记录（判断是否有病历）
    appointment_ids = [a.id for a in appointments]
    medical_records = {}
    if appointment_ids:
        result = await db.execute(
            select(MedicalRecord.appointment_id).where(
                MedicalRecord.appointment_id.in_(appointment_ids)
            )
        )
        medical_records = {row[0]: True for row in result.fetchall()}

    return {
        "items": [
            PatientHistoryResponse(
                id=a.id,
                appointment_no=a.appointment_no,
                schedule_date=a.schedule.schedule_date if a.schedule else None,
                time_slot=a.schedule.time_slot if a.schedule else None,
                status=a.status,
                complete_time=a.complete_time,
                symptom_description=a.symptom_description,
                has_medical_record=medical_records.get(a.id, False),
            )
            for a in appointments
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/appointments/{appointment_id}/follow-up", summary="创建复诊预约")
async def create_follow_up_booking(
    appointment_id: str,
    request: FollowUpBookingRequest,
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db)
):
    """为患者创建复诊预约

    基于原预约的患者信息，在指定排班下创建新的预约。
    原预约必须属于当前医生且已完成。
    """
    from app.modules.appointments.service import _verify_appointment_ownership

    # 验证原预约属于当前医生
    original = await _verify_appointment_ownership(appointment_id, doctor, db)

    # 验证原预约已完成
    if original.status != 5:  # COMPLETED
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能为已完成的预约创建复诊"
        )

    service = AppointmentService(db)

    try:
        # 创建新预约
        new_appointment = await service.create(
            user_id=original.user_id,
            patient_id=original.patient_id,
            schedule_id=request.schedule_id,
            symptom_description=f"复诊（原预约号：{original.appointment_no}）",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {
        "message": "复诊预约创建成功",
        "appointment_id": new_appointment.id,
        "appointment_no": new_appointment.appointment_no,
    }
