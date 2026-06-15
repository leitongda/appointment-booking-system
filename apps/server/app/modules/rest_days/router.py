import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.modules.rest_days.service import RestDayService
from app.schemas.response import PageResponse
from app.schemas.rest_day import (
    RestDayCreate,
    RestDayResponse,
)

router = APIRouter()


@router.get("", response_model=PageResponse[RestDayResponse], summary="获取列表")
async def get_rest_days(
    store_id: str | None = None,
    doctor_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    status: int | None = Query(None, ge=0, le=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db)
):
    """获取休息日列表"""
    service = RestDayService(db)
    rest_days, total = await service.get_list(
        store_id=store_id,
        doctor_id=doctor_id,
        start_date=start_date,
        end_date=end_date,
        status=status,
        page=page,
        page_size=page_size
    )
    
    # 批量获取医生姓名，避免 N+1 查询
    doctor_ids_list = []
    for rd in rest_days:
        if rd.doctor_ids:
            try:
                doctor_ids = json.loads(rd.doctor_ids)
                doctor_ids_list.append(doctor_ids)
            except:
                doctor_ids_list.append([])
        else:
            doctor_ids_list.append([])

    # 批量查询所有医生姓名
    doctor_names_batch = await service.get_doctor_names_batch(doctor_ids_list)

    result = []
    for rd in rest_days:
        doctor_ids = None
        doctor_names = None
        if rd.doctor_ids:
            try:
                doctor_ids = json.loads(rd.doctor_ids)
                key = tuple(sorted(doctor_ids))
                doctor_names = doctor_names_batch.get(key, [])
            except:
                pass

        result.append(RestDayResponse(
            id=rd.id,
            store_id=rd.store_id,
            store_name=rd.store.name if rd.store else None,
            doctor_ids=doctor_ids,
            doctor_names=doctor_names,
            reason=rd.reason,
            start_date=rd.start_date,
            end_date=rd.end_date,
            status=rd.status,
            created_at=rd.created_at
        ))
    
    return PageResponse(data=result, total=total, page=page, page_size=page_size)


@router.post("", response_model=RestDayResponse, summary="添加休息日")
async def create_rest_day(
    data: RestDayCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:create"))
):
    """添加休息日"""
    service = RestDayService(db)
    
    # 验证日期范围
    if data.start_date > data.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="开始日期不能大于结束日期，请检查后重试"
        )
    
    rest_day = await service.create(data)
    
    doctor_ids = None
    doctor_names = None
    if rest_day.doctor_ids:
        try:
            doctor_ids = json.loads(rest_day.doctor_ids)
            doctor_names = await service.get_doctor_names(doctor_ids)
        except:
            pass
    
    return RestDayResponse(
        id=rest_day.id,
        store_id=rest_day.store_id,
        store_name=None,
        doctor_ids=doctor_ids,
        doctor_names=doctor_names,
        reason=rest_day.reason,
        start_date=rest_day.start_date,
        end_date=rest_day.end_date,
        status=rest_day.status,
        created_at=rest_day.created_at
    )


@router.delete("/{rest_day_id}", summary="删除休息日")
async def delete_rest_day(
    rest_day_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:delete"))
):
    """删除休息日"""
    service = RestDayService(db)
    success = await service.delete(rest_day_id)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="休息日记录不存在，请检查后重试")
    
    return {"message": "删除成功"}


@router.put("/{rest_day_id}/cancel", summary="取消休息日")
async def cancel_rest_day(
    rest_day_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:update"))
):
    """取消休息日"""
    service = RestDayService(db)
    rest_day = await service.cancel(rest_day_id)
    
    if not rest_day:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="休息日记录不存在，请检查后重试")
    
    return {"message": "取消成功"}
