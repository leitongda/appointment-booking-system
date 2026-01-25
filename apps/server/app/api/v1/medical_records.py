"""病历管理 API"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import date

from app.db.session import get_db
from app.api.deps import get_current_user
from app.schemas.medical_record import (
    MedicalRecordCreate,
    MedicalRecordUpdate,
    MedicalRecordResponse,
    MedicalRecordListResponse,
)
from app.schemas.response import PageResponse
from app.services.medical_record_service import MedicalRecordService
from app.core.config import settings

router = APIRouter()


def build_record_response(record) -> MedicalRecordResponse:
    """构建病历响应"""
    return MedicalRecordResponse(
        id=record.id,
        record_no=record.record_no,
        appointment_id=record.appointment_id,
        patient_id=record.patient_id,
        patient_name=record.patient.name if record.patient else None,
        patient_phone=record.patient.phone if record.patient else None,
        patient_gender=record.patient.gender if record.patient else None,
        doctor_id=record.doctor_id,
        doctor_name=record.doctor.name if record.doctor else None,
        department_id=record.department_id,
        department_name=record.department.name if record.department else None,
        chief_complaint=record.chief_complaint,
        present_illness=record.present_illness,
        past_history=record.past_history,
        allergy_history=record.allergy_history,
        physical_exam=record.physical_exam,
        auxiliary_exam=record.auxiliary_exam,
        diagnosis=record.diagnosis,
        treatment=record.treatment,
        prescription=record.prescription,
        advice=record.advice,
        total_fee=float(record.total_fee) if record.total_fee else 0,
        status=record.status,
        visit_date=record.visit_date,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def build_list_response(record) -> MedicalRecordListResponse:
    """构建病历列表响应"""
    return MedicalRecordListResponse(
        id=record.id,
        record_no=record.record_no,
        patient_name=record.patient.name if record.patient else None,
        doctor_name=record.doctor.name if record.doctor else None,
        department_name=record.department.name if record.department else None,
        diagnosis=record.diagnosis,
        visit_date=record.visit_date,
        status=record.status,
        created_at=record.created_at,
    )


@router.get("", response_model=PageResponse[MedicalRecordListResponse])
async def get_medical_records(
    doctor_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    department_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[int] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取病历列表"""
    service = MedicalRecordService(db)
    records, total = await service.get_list(
        doctor_id=doctor_id,
        patient_id=patient_id,
        department_id=department_id,
        start_date=start_date,
        end_date=end_date,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    
    result = [build_list_response(r) for r in records]
    return PageResponse(data=result, total=total, page=page, page_size=page_size)


@router.get("/my", response_model=PageResponse[MedicalRecordListResponse])
async def get_my_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取当前医生的病历列表"""
    doctor_id = current_user.get("doctor_id")
    if not doctor_id:
        return PageResponse(data=[], total=0, page=page, page_size=page_size)
    
    service = MedicalRecordService(db)
    records, total = await service.get_list(
        doctor_id=doctor_id,
        page=page,
        page_size=page_size,
    )
    
    result = [build_list_response(r) for r in records]
    return PageResponse(data=result, total=total, page=page, page_size=page_size)


@router.get("/patient/{patient_id}", response_model=PageResponse[MedicalRecordListResponse])
async def get_patient_records(
    patient_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取患者的病历列表"""
    service = MedicalRecordService(db)
    records, total = await service.get_patient_records(
        patient_id=patient_id,
        page=page,
        page_size=page_size,
    )
    
    result = [build_list_response(r) for r in records]
    return PageResponse(data=result, total=total, page=page, page_size=page_size)


@router.get("/appointment/{appointment_id}", response_model=MedicalRecordResponse)
async def get_record_by_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """根据预约ID获取病历"""
    service = MedicalRecordService(db)
    record = await service.get_by_appointment(appointment_id)
    
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="病历不存在，请检查后重试")
    
    return build_record_response(record)


@router.get("/{record_id}", response_model=MedicalRecordResponse)
async def get_medical_record(
    record_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取病历详情"""
    service = MedicalRecordService(db)
    record = await service.get_by_id(record_id)
    
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="病历不存在，请检查后重试")
    
    return build_record_response(record)


@router.post("", response_model=MedicalRecordResponse)
async def create_medical_record(
    data: MedicalRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """创建病历"""
    doctor_id = current_user.get("doctor_id")
    if not doctor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要医生权限，请联系管理员开通")
    
    service = MedicalRecordService(db)
    
    try:
        record = await service.create(doctor_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    # 重新获取完整信息
    record = await service.get_by_id(record.id)
    return build_record_response(record)


@router.put("/{record_id}", response_model=MedicalRecordResponse)
async def update_medical_record(
    record_id: str,
    data: MedicalRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """更新病历"""
    service = MedicalRecordService(db)
    record = await service.update(record_id, data)
    
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="病历不存在，请检查后重试")
    
    # 重新获取完整信息
    record = await service.get_by_id(record_id)
    return build_record_response(record)


@router.delete("/{record_id}")
async def delete_medical_record(
    record_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """删除病历"""
    service = MedicalRecordService(db)
    success = await service.delete(record_id)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="病历不存在，请检查后重试")
    
    return {"message": "删除成功"}

