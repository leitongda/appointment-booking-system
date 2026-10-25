
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_admin,
    get_current_user,
    require_permission,
    require_tenant_active_for_write,
)
from app.core.config import settings
from app.db.session import get_db
from app.modules.doctor_reviews.schemas import (
    DoctorReviewPatientCreate,
    DoctorReviewPatientItem,
    DoctorReviewPatientListResponse,
    DoctorReviewReply,
    DoctorReviewResponse,
)
from app.modules.doctor_reviews.service import DoctorReviewService
from app.schemas.response import PageResponse

router = APIRouter()


@router.post("", response_model=DoctorReviewResponse, summary="创建医生评价（患者端）")
async def create_review(
    data: DoctorReviewPatientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _tenant_guard: None = Depends(require_tenant_active_for_write),
):
    """患者提交医生评价：rating 1-5，content 非空且不超过 1000 字"""
    service = DoctorReviewService(db)
    review = await service.create_from_patient(user_id=current_user["id"], data=data)
    return DoctorReviewResponse(
        id=review.id,
        appointment_id=review.appointment_id,
        doctor_id=review.doctor_id,
        user_id=review.user_id,
        patient_id=review.patient_id,
        rating=review.rating,
        content=review.content,
        tags=review.tags,
        is_anonymous=review.is_anonymous,
        status=review.status,
        reply=review.reply,
        reply_at=review.reply_at,
        created_at=review.created_at,
    )


@router.get("", response_model=DoctorReviewPatientListResponse, summary="获取医生评价列表（患者端）")
async def get_reviews(
    doctor_id: str = Query(..., description="医生ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
):
    """按医生查询评价：仅展示正常状态，按创建时间倒序，就诊人姓名脱敏"""
    service = DoctorReviewService(db)
    reviews, total = await service.get_by_doctor(
        doctor_id=doctor_id,
        page=page,
        page_size=page_size,
    )
    items = [
        DoctorReviewPatientItem(
            id=r["id"],
            doctor_id=r["doctor_id"],
            rating=r["rating"],
            content=r["content"],
            tags=r["tags"],
            reply=r["reply"],
            reply_at=r["reply_at"],
            created_at=r["created_at"],
            patient_name=DoctorReviewService.mask_patient_name(r.get("patient_name")),
        )
        for r in reviews
    ]
    return DoctorReviewPatientListResponse(items=items, total=total)


@router.get("/doctors/{doctor_id}", response_model=PageResponse[DoctorReviewResponse], summary="获取医生评价")
async def get_doctor_reviews(
    doctor_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
):
    service = DoctorReviewService(db)
    reviews, total = await service.get_by_doctor(
        doctor_id=doctor_id,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        data=[
            DoctorReviewResponse(
                **{**r, "patient_name": DoctorReviewService.mask_patient_name(r.get("patient_name"))}
            )
            for r in reviews
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/{review_id}/reply", response_model=DoctorReviewResponse, summary="回复评价")
async def reply_review(
    review_id: str,
    data: DoctorReviewReply,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("doctor:review")),
):
    service = DoctorReviewService(db)
    operator_id = current_admin.get("id")
    review = await service.reply(review_id, operator_id, data)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评价不存在")
    return DoctorReviewResponse(
        id=review.id,
        appointment_id=review.appointment_id,
        doctor_id=review.doctor_id,
        user_id=review.user_id,
        patient_id=review.patient_id,
        rating=review.rating,
        content=review.content,
        tags=review.tags,
        is_anonymous=review.is_anonymous,
        status=review.status,
        reply=review.reply,
        reply_at=review.reply_at,
        created_at=review.created_at,
    )
