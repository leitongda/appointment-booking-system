from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_tenant_active_for_write
from app.db.session import get_db
from app.modules.appointment_satisfactions.schemas import (
    AppointmentSatisfactionCreate,
    AppointmentSatisfactionResponse,
)
from app.modules.appointment_satisfactions.service import AppointmentSatisfactionService

router = APIRouter()


@router.post(
    "/appointments/{appointment_id}/satisfaction",
    response_model=AppointmentSatisfactionResponse,
    summary="提交预约满意度",
)
async def create_satisfaction(
    appointment_id: str,
    data: AppointmentSatisfactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _tenant_guard: None = Depends(require_tenant_active_for_write),
):
    service = AppointmentSatisfactionService(db)
    try:
        satisfaction = await service.create(
            appointment_id=appointment_id,
            user_id=current_user["id"],
            data=data,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return AppointmentSatisfactionResponse(
        id=satisfaction.id,
        appointment_id=satisfaction.appointment_id,
        user_id=satisfaction.user_id,
        patient_id=satisfaction.patient_id,
        doctor_id=satisfaction.doctor_id,
        overall_score=satisfaction.overall_score,
        service_score=satisfaction.service_score,
        environment_score=satisfaction.environment_score,
        comment=satisfaction.comment,
        tags=satisfaction.tags,
        submitted_at=satisfaction.submitted_at,
        created_at=satisfaction.created_at,
    )


@router.get(
    "/appointments/{appointment_id}/satisfaction",
    response_model=AppointmentSatisfactionResponse,
    summary="获取预约满意度",
)
async def get_satisfaction(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = AppointmentSatisfactionService(db)
    satisfaction = await service.get_by_appointment(appointment_id)
    if not satisfaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="满意度评价不存在")
    return AppointmentSatisfactionResponse(
        id=satisfaction.id,
        appointment_id=satisfaction.appointment_id,
        user_id=satisfaction.user_id,
        patient_id=satisfaction.patient_id,
        doctor_id=satisfaction.doctor_id,
        overall_score=satisfaction.overall_score,
        service_score=satisfaction.service_score,
        environment_score=satisfaction.environment_score,
        comment=satisfaction.comment,
        tags=satisfaction.tags,
        submitted_at=satisfaction.submitted_at,
        created_at=satisfaction.created_at,
    )
