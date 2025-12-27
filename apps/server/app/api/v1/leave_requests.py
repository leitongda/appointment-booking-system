from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import date

from app.db.session import get_db
from app.api.deps import get_current_admin, get_store_filter
from app.schemas.leave_request import (
    StopClinicCreate, ScheduleChangeCreate, ReviewRequest,
    LeaveRequestResponse, LeaveRequestQuery, RequestType, RequestStatus
)
from app.schemas.response import PageResponse
from app.services.leave_request_service import LeaveRequestService

router = APIRouter()


@router.get("", response_model=PageResponse[LeaveRequestResponse])
async def get_leave_requests(
    doctor_id: Optional[str] = None,
    request_type: Optional[RequestType] = None,
    status: Optional[RequestStatus] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取申请列表（管理端）"""
    # 获取门店过滤
    store_filter = get_store_filter(current_admin)
    
    service = LeaveRequestService(db)
    query = LeaveRequestQuery(
        doctor_id=doctor_id,
        request_type=request_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
        store_id=store_filter if isinstance(store_filter, str) else None
    )
    requests, total = await service.get_list(query)
    
    return PageResponse(
        data=[LeaveRequestResponse.model_validate(r) for r in requests],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/pending-count")
async def get_pending_count(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取待审核数量"""
    # 获取门店过滤
    store_filter = get_store_filter(current_admin)
    store_id = store_filter if isinstance(store_filter, str) else None
    
    service = LeaveRequestService(db)
    count = await service.get_pending_count(store_id=store_id)
    return {"count": count}


@router.get("/my", response_model=List[LeaveRequestResponse])
async def get_my_requests(
    doctor_id: str = Query(..., description="医生ID"),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取我的申请列表（医生端）"""
    service = LeaveRequestService(db)
    requests = await service.get_doctor_requests(doctor_id, status)
    return [LeaveRequestResponse.model_validate(r) for r in requests]


@router.get("/{request_id}", response_model=LeaveRequestResponse)
async def get_leave_request(
    request_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取申请详情"""
    service = LeaveRequestService(db)
    request = await service.get_by_id(request_id)
    
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="申请不存在，请检查后重试"
        )
    
    return LeaveRequestResponse.model_validate(request)


@router.post("/stop-clinic", response_model=LeaveRequestResponse)
async def create_stop_clinic_request(
    data: StopClinicCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建停诊申请"""
    service = LeaveRequestService(db)
    request = await service.create_stop_clinic(data)
    return LeaveRequestResponse.model_validate(request)


@router.post("/schedule-change", response_model=LeaveRequestResponse)
async def create_schedule_change_request(
    data: ScheduleChangeCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建调班申请"""
    service = LeaveRequestService(db)
    request = await service.create_schedule_change(data)
    return LeaveRequestResponse.model_validate(request)


@router.post("/{request_id}/review", response_model=LeaveRequestResponse)
async def review_request(
    request_id: str,
    data: ReviewRequest,
    reviewer_id: str = Query(..., description="审核人ID"),
    db: AsyncSession = Depends(get_db)
):
    """审核申请"""
    service = LeaveRequestService(db)
    
    try:
        request = await service.review(request_id, reviewer_id, data)
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="申请不存在，请检查后重试"
            )
        return LeaveRequestResponse.model_validate(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{request_id}/cancel")
async def cancel_request(
    request_id: str,
    doctor_id: str = Query(..., description="医生ID"),
    db: AsyncSession = Depends(get_db)
):
    """取消申请"""
    service = LeaveRequestService(db)
    
    try:
        success = await service.cancel(request_id, doctor_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="申请不存在，请检查后重试"
            )
        return {"message": "取消成功"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
