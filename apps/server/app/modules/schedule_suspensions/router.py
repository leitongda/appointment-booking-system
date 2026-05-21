"""停诊管理路由"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import date
import json

from app.db.session import get_db
from app.api.deps import get_current_admin, require_permission
from app.schemas.schedule_suspension import (
    ScheduleSuspensionCreate,
    ScheduleSuspensionResponse,
    AvailableScheduleForSuspension,
    SuspensionProcessRequest,
    SuspensionProcessResult,
)
from app.schemas.response import PageResponse
from app.modules.schedule_suspensions.service import ScheduleSuspensionService
from app.core.config import settings

router = APIRouter()


@router.get("", response_model=PageResponse[ScheduleSuspensionResponse], summary="获取停诊列表")
async def get_schedule_suspensions(
    store_id: Optional[str] = None,
    doctor_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[int] = Query(None, ge=0, le=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:read"))
):
    """获取停诊列表"""
    service = ScheduleSuspensionService(db)
    suspensions, total = await service.get_list(
        store_id=store_id,
        doctor_id=doctor_id,
        start_date=start_date,
        end_date=end_date,
        status=status,
        page=page,
        page_size=page_size
    )

    result = []
    for s in suspensions:
        schedule_ids = None
        time_slots = None
        if s.schedule_ids:
            try:
                schedule_ids = json.loads(s.schedule_ids)
            except Exception:
                pass
        if s.time_slots:
            try:
                time_slots = json.loads(s.time_slots)
            except Exception:
                pass

        result.append(ScheduleSuspensionResponse(
            id=s.id,
            store_id=s.store_id,
            store_name=s.store.name if s.store else None,
            doctor_id=s.doctor_id,
            doctor_name=s.doctor.name if s.doctor else None,
            title=s.title,
            suspension_date=s.suspension_date,
            schedule_ids=schedule_ids,
            time_slots=time_slots,
            status=s.status,
            created_at=s.created_at,
            suspension_type=s.suspension_type,
            processing_method=s.processing_method,
            processing_status=s.processing_status,
            affected_appointment_count=s.affected_appointment_count,
            reason=s.reason,
        ))

    return PageResponse(data=result, total=total, page=page, page_size=page_size)


@router.get("/schedules", response_model=List[AvailableScheduleForSuspension], summary="获取可选排班列表")
async def get_available_schedules_for_suspension(
    store_id: str = Query(...),
    doctor_id: str = Query(...),
    suspension_date: date = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """获取指定日期的可选排班（用于停诊选择）"""
    service = ScheduleSuspensionService(db)
    return await service.get_available_schedules(store_id, doctor_id, suspension_date)


@router.post("", response_model=ScheduleSuspensionResponse, summary="创建停诊")
async def create_schedule_suspension(
    data: ScheduleSuspensionCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:suspend"))
):
    """创建停诊"""
    service = ScheduleSuspensionService(db)
    suspension = await service.create(data)

    schedule_ids = None
    time_slots = None
    if suspension.schedule_ids:
        try:
            schedule_ids = json.loads(suspension.schedule_ids)
        except Exception:
            pass
    if suspension.time_slots:
        try:
            time_slots = json.loads(suspension.time_slots)
        except Exception:
            pass

    return ScheduleSuspensionResponse(
        id=suspension.id,
        store_id=suspension.store_id,
        store_name=None,
        doctor_id=suspension.doctor_id,
        doctor_name=None,
        title=suspension.title,
        suspension_date=suspension.suspension_date,
        schedule_ids=schedule_ids,
        time_slots=time_slots,
        status=suspension.status,
        created_at=suspension.created_at,
        suspension_type=suspension.suspension_type,
        processing_method=suspension.processing_method,
        processing_status=suspension.processing_status,
        affected_appointment_count=suspension.affected_appointment_count,
        reason=suspension.reason,
    )


@router.post("/{suspension_id}/process", summary="处置停诊影响的患者")
async def process_suspension(
    suspension_id: str,
    data: SuspensionProcessRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:suspend")),
):
    """处置停诊影响的患者

    处置方式:
    - auto_refund: 自动取消预约并触发退款
    - reschedule: 标记为待转约，通知患者选择其他医生
    - change_date: 标记为待改期，通知患者选择其他日期
    - manual: 仅记录，等待人工处理
    """
    from app.modules.schedule_suspensions.service_processing import SuspensionProcessingService
    service = SuspensionProcessingService(db)
    operator_id = current_admin.get("id") if current_admin else None
    try:
        result = await service.process_suspension(
            suspension_id=suspension_id,
            processing_method=data.processing_method,
            operator_id=operator_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{suspension_id}/affected-count", summary="统计停诊影响的预约数")
async def get_affected_appointment_count(
    suspension_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:read")),
):
    """统计停诊影响的活跃预约数量"""
    from app.modules.schedule_suspensions.service_processing import SuspensionProcessingService
    service = SuspensionProcessingService(db)
    try:
        count = await service.count_affected_appointments(suspension_id)
        return {"affected_count": count}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{suspension_id}", summary="删除停诊记录")
async def delete_schedule_suspension(
    suspension_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:delete"))
):
    """删除停诊记录"""
    service = ScheduleSuspensionService(db)
    success = await service.delete(suspension_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="停诊记录不存在，请检查后重试")

    return {"message": "删除成功"}


@router.put("/{suspension_id}/cancel", summary="取消停诊")
async def cancel_schedule_suspension(
    suspension_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:suspend"))
):
    """取消停诊"""
    service = ScheduleSuspensionService(db)
    suspension = await service.cancel(suspension_id)

    if not suspension:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="停诊记录不存在，请检查后重试")

    return {"message": "取消成功"}
