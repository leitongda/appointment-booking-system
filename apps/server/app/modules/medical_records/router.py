from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_or_admin, resolve_actor_tenant_anchor
from app.core.config import settings
from app.db.session import get_db
from app.modules.examination_reports.service import ExaminationReportService
from app.modules.medical_records.service import MedicalRecordService
from app.schemas.medical_record import (
    MedicalRecordCreate,
    MedicalRecordListResponse,
    MedicalRecordResponse,
    MedicalRecordUpdate,
)
from app.schemas.response import PageResponse

router = APIRouter()


async def _ensure_patient_own_access(db: AsyncSession, current_user: dict, patient_id: str) -> None:
    """患者端水平越权校验：只能访问自己名下的就诊人（医生/管理员放行）。

    不区分「不存在」与「他人就诊人」，统一 404，防止枚举。
    """
    if current_user.get("is_admin") or current_user.get("is_doctor"):
        return

    from app.models.user import Patient

    patient = await db.get(Patient, patient_id)
    if not patient or patient.user_id != current_user.get("id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="就诊人不存在")


def build_record_response(record) -> MedicalRecordResponse:
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


@router.get("", response_model=PageResponse[MedicalRecordListResponse], summary="获取列表")
async def get_medical_records(
    doctor_id: str | None = None,
    patient_id: str | None = None,
    department_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    status: int | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = MedicalRecordService(db, resolve_actor_tenant_anchor(current_user))
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
    return PageResponse(data=[build_list_response(r) for r in records], total=total, page=page, page_size=page_size)


@router.get("/my", response_model=PageResponse[MedicalRecordListResponse], summary="获取我的列表")
async def get_my_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    doctor_id = current_user.get("doctor_id")
    if not doctor_id:
        return PageResponse(data=[], total=0, page=page, page_size=page_size)
    service = MedicalRecordService(db, resolve_actor_tenant_anchor(current_user))
    records, total = await service.get_list(doctor_id=doctor_id, page=page, page_size=page_size)
    return PageResponse(data=[build_list_response(r) for r in records], total=total, page=page, page_size=page_size)


@router.get("/patient/{patient_id}", response_model=PageResponse[MedicalRecordListResponse], summary="获取患者列表")
async def get_patient_records(
    patient_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = MedicalRecordService(db, resolve_actor_tenant_anchor(current_user))
    await _ensure_patient_own_access(db, current_user, patient_id)
    records, total = await service.get_patient_records(patient_id=patient_id, page=page, page_size=page_size)
    return PageResponse(data=[build_list_response(r) for r in records], total=total, page=page, page_size=page_size)


@router.get("/appointment/{appointment_id}", response_model=MedicalRecordResponse, summary="根据预约获取")
async def get_record_by_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = MedicalRecordService(db, resolve_actor_tenant_anchor(current_user))
    record = await service.get_by_appointment(appointment_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="病历不存在，请检查后重试")
    await _ensure_patient_own_access(db, current_user, record.patient_id)
    response = build_record_response(record)
    # 附带检查报告
    report_service = ExaminationReportService(db)
    reports = await report_service.get_by_appointment(appointment_id)
    response.examination_reports = [
        {"id": r.id, "title": r.title, "reportType": r.report_type, "fileName": r.file_name, "fileSize": r.file_size, "fileType": r.file_type, "fileUrl": r.file_url, "createdAt": r.created_at.isoformat() if r.created_at else None}
        for r in reports
    ]
    return response


@router.get("/{record_id}", response_model=MedicalRecordResponse, summary="获取详情")
async def get_medical_record(
    record_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = MedicalRecordService(db, resolve_actor_tenant_anchor(current_user))
    record = await service.get_by_id(record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="病历不存在，请检查后重试")
    await _ensure_patient_own_access(db, current_user, record.patient_id)
    response = build_record_response(record)
    # 附带检查报告
    report_service = ExaminationReportService(db)
    reports = await report_service.get_by_record(record_id)
    response.examination_reports = [
        {"id": r.id, "title": r.title, "reportType": r.report_type, "fileName": r.file_name, "fileSize": r.file_size, "fileType": r.file_type, "fileUrl": r.file_url, "createdAt": r.created_at.isoformat() if r.created_at else None}
        for r in reports
    ]
    return response


@router.post("", response_model=MedicalRecordResponse, summary="创建病历")
async def create_medical_record(
    data: MedicalRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    doctor_id = current_user.get("doctor_id")
    if not doctor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要医生权限，请联系管理员开通")
    service = MedicalRecordService(db, resolve_actor_tenant_anchor(current_user))
    try:
        record = await service.create(doctor_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    record = await service.get_by_id(record.id)
    return build_record_response(record)


@router.put("/{record_id}", response_model=MedicalRecordResponse, summary="更新病历")
async def update_medical_record(
    record_id: str,
    data: MedicalRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    if not current_user.get("is_admin") and not current_user.get("is_doctor"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅医生或管理员可修改病历")
    service = MedicalRecordService(db, resolve_actor_tenant_anchor(current_user))
    record = await service.update(record_id, data)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="病历不存在，请检查后重试")
    record = await service.get_by_id(record_id)
    return build_record_response(record)


@router.delete("/{record_id}", summary="删除病历")
async def delete_medical_record(
    record_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = MedicalRecordService(db, resolve_actor_tenant_anchor(current_user))
    record = await service.get_by_id(record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="病历不存在，请检查后重试")

    # 权限校验：仅创建医生或管理员可删除
    doctor_id = current_user.get("doctor_id")
    is_admin = current_user.get("is_admin")
    if not is_admin and record.doctor_id != doctor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅创建医生或管理员可删除病历")

    operator_id = doctor_id or current_user.get("admin_id") or current_user.get("sub")
    success = await service.delete(record_id, operator_id=operator_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="病历不存在，请检查后重试")
    return {"message": "删除成功"}
