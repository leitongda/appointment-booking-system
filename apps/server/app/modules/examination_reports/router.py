"""检查报告路由"""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_or_admin, get_current_admin
from app.core.config import settings
from app.core.logging import logger
from app.db.session import get_db
from app.infrastructure.storage import get_storage
from app.infrastructure.storage.base import build_tenant_storage_folder
from app.modules.examination_reports.schemas import (
    ExaminationReportCreate,
    ExaminationReportListResponse,
    ExaminationReportResponse,
)
from app.modules.examination_reports.service import ExaminationReportService
from app.schemas.response import PageResponse

router = APIRouter()


@router.get("", response_model=PageResponse[ExaminationReportListResponse], summary="获取报告列表")
async def list_reports(
    keyword: Optional[str] = Query(None, description="关键字搜索（标题/文件名）"),
    report_type: Optional[str] = Query(None, alias="reportType", description="报告类型"),
    store_id: Optional[str] = Query(None, alias="storeId", description="门店ID"),
    doctor_id: Optional[str] = Query(None, alias="doctorId", description="医生ID"),
    patient_id: Optional[str] = Query(None, alias="patientId", description="患者ID"),
    start_date: Optional[str] = Query(None, alias="startDate", description="开始日期"),
    end_date: Optional[str] = Query(None, alias="endDate", description="结束日期"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    """管理端：获取报告列表（支持多条件筛选）"""
    service = ExaminationReportService(db)
    reports, total = await service.get_list(
        keyword=keyword,
        report_type=report_type,
        store_id=store_id,
        doctor_id=doctor_id,
        patient_id=patient_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        data=[_build_list_response(r) for r in reports],
        total=total,
        page=page,
        page_size=page_size,
    )

ALLOWED_REPORT_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
MAX_REPORT_SIZE = 20 * 1024 * 1024  # 20MB
REPORT_TYPE_OPTIONS = ["blood_test", "imaging", "pathology", "other"]


def _build_report_response(report) -> ExaminationReportResponse:
    resp = ExaminationReportResponse.model_validate(report)
    resp.patient_name = report.patient.name if report.patient else None
    resp.doctor_name = report.doctor.name if report.doctor else None
    return resp


def _build_list_response(report) -> ExaminationReportListResponse:
    return ExaminationReportListResponse.model_validate(report)


@router.post("/upload", response_model=ExaminationReportResponse, summary="上传检查报告")
async def upload_report(
    file: UploadFile = File(...),
    appointment_id: str = Form(...),
    record_id: Optional[str] = Form(None),
    report_type: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    """医生上传检查报告文件"""
    doctor_id = current_user.get("doctor_id")
    if not doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要医生权限",
        )

    # 校验报告类型
    if report_type not in REPORT_TYPE_OPTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的报告类型，可选: {', '.join(REPORT_TYPE_OPTIONS)}",
        )

    # 校验文件类型
    if file.content_type not in ALLOWED_REPORT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的文件格式，请使用 PDF、JPEG、PNG 或 WebP 格式",
        )

    # 读取文件内容并校验大小
    content = await file.read()
    if len(content) > MAX_REPORT_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制，最大支持 {MAX_REPORT_SIZE // 1024 // 1024}MB",
        )
    await file.seek(0)

    # 上传到存储
    try:
        storage = get_storage()
        filename = file.filename or "report.pdf"
        tenant_id = current_user.get("tenant_id")
        tenant_folder = build_tenant_storage_folder("reports", tenant_id)

        result = await storage.upload(
            file=file.file,
            filename=filename,
            content_type=file.content_type,
            folder=tenant_folder,
        )
        logger.info(f"检查报告上传成功: {result.key} by doctor {doctor_id}")
    except Exception as exc:
        logger.error(f"检查报告上传失败: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件上传失败",
        ) from exc

    # 创建报告记录
    service = ExaminationReportService(db)
    try:
        create_data = ExaminationReportCreate(
            appointmentId=appointment_id,
            recordId=record_id,
            reportType=report_type,
            title=title,
            description=description,
            fileName=filename,
            fileKey=result.key,
            fileSize=result.size,
            fileType=result.content_type,
            fileUrl=result.url,
        )
        report = await service.create(doctor_id, create_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    report = await service.get_by_id(report.id)
    return _build_report_response(report)


@router.get("/appointment/{appointment_id}", response_model=list[ExaminationReportListResponse], summary="按预约获取报告")
async def get_reports_by_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = ExaminationReportService(db)
    reports = await service.get_by_appointment(appointment_id)
    return [_build_list_response(r) for r in reports]


@router.get("/patient/{patient_id}", response_model=PageResponse[ExaminationReportListResponse], summary="按患者获取报告")
async def get_reports_by_patient(
    patient_id: str,
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = ExaminationReportService(db)
    reports, total = await service.get_by_patient(
        patient_id=patient_id,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        data=[_build_list_response(r) for r in reports],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/record/{record_id}", response_model=list[ExaminationReportListResponse], summary="按病历获取报告")
async def get_reports_by_record(
    record_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = ExaminationReportService(db)
    reports = await service.get_by_record(record_id)
    return [_build_list_response(r) for r in reports]


@router.get("/{report_id}", response_model=ExaminationReportResponse, summary="获取报告详情")
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = ExaminationReportService(db)
    report = await service.get_by_id(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在",
        )
    return _build_report_response(report)


@router.delete("/{report_id}", summary="删除报告")
async def delete_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    doctor_id = current_user.get("doctor_id")
    if not doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要医生权限",
        )

    service = ExaminationReportService(db)
    try:
        success = await service.delete(report_id, doctor_id)
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在",
        )
    return {"message": "删除成功"}
