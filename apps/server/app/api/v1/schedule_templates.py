from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.schemas.schedule_template import (
    ScheduleTemplateCreate,
    ScheduleTemplateUpdate,
    ScheduleTemplateResponse,
    ScheduleGenerateRequest,
    ScheduleBatchAddRequest,
)
from app.schemas.response import PageResponse
from app.services.schedule_template_service import ScheduleTemplateService

router = APIRouter()


@router.get("", response_model=PageResponse[ScheduleTemplateResponse])
async def get_templates(
    store_id: Optional[str] = None,
    doctor_id: Optional[str] = None,
    department_id: Optional[str] = None,
    status: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取排班模板列表"""
    service = ScheduleTemplateService(db)
    templates, total = await service.get_list(
        store_id=store_id,
        doctor_id=doctor_id,
        department_id=department_id,
        status=status,
        page=page,
        page_size=page_size
    )
    
    result = []
    for t in templates:
        result.append(ScheduleTemplateResponse(
            id=t.id,
            name=t.name,
            store_id=t.store_id,
            doctor_id=t.doctor_id,
            department_id=t.department_id,
            weekday=t.weekday,
            appointment_type=t.appointment_type,
            start_time=t.start_time,
            end_time=t.end_time,
            total_slots=t.total_slots,
            schedule_mode=t.schedule_mode,
            status=t.status,
            store_name=t.store.name if t.store else None,
            doctor_name=t.doctor.name if t.doctor else None,
            department_name=t.department.name if t.department else None,
            created_at=t.created_at,
            updated_at=t.updated_at
        ))
    
    return PageResponse(data=result, total=total, page=page, page_size=page_size)


@router.get("/{template_id}", response_model=ScheduleTemplateResponse)
async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
    """获取排班模板详情"""
    service = ScheduleTemplateService(db)
    template = await service.get_by_id(template_id)
    
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    
    return ScheduleTemplateResponse(
        id=template.id,
        name=template.name,
        store_id=template.store_id,
        doctor_id=template.doctor_id,
        department_id=template.department_id,
        weekday=template.weekday,
        appointment_type=template.appointment_type,
        start_time=template.start_time,
        end_time=template.end_time,
        total_slots=template.total_slots,
        schedule_mode=template.schedule_mode,
        status=template.status,
        store_name=template.store.name if template.store else None,
        doctor_name=template.doctor.name if template.doctor else None,
        department_name=template.department.name if template.department else None,
        created_at=template.created_at,
        updated_at=template.updated_at
    )


@router.post("", response_model=ScheduleTemplateResponse)
async def create_template(
    data: ScheduleTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """创建排班模板"""
    service = ScheduleTemplateService(db)
    
    try:
        template = await service.create(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    # 重新加载关联数据
    template = await service.get_by_id(template.id)
    
    return ScheduleTemplateResponse(
        id=template.id,
        name=template.name,
        store_id=template.store_id,
        doctor_id=template.doctor_id,
        department_id=template.department_id,
        weekday=template.weekday,
        appointment_type=template.appointment_type,
        start_time=template.start_time,
        end_time=template.end_time,
        total_slots=template.total_slots,
        schedule_mode=template.schedule_mode,
        status=template.status,
        store_name=template.store.name if template.store else None,
        doctor_name=template.doctor.name if template.doctor else None,
        department_name=template.department.name if template.department else None,
        created_at=template.created_at,
        updated_at=template.updated_at
    )


@router.put("/{template_id}", response_model=ScheduleTemplateResponse)
async def update_template(
    template_id: str,
    data: ScheduleTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """更新排班模板"""
    service = ScheduleTemplateService(db)
    
    try:
        template = await service.update(template_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    
    # 重新加载关联数据
    template = await service.get_by_id(template.id)
    
    return ScheduleTemplateResponse(
        id=template.id,
        name=template.name,
        store_id=template.store_id,
        doctor_id=template.doctor_id,
        department_id=template.department_id,
        weekday=template.weekday,
        appointment_type=template.appointment_type,
        start_time=template.start_time,
        end_time=template.end_time,
        total_slots=template.total_slots,
        schedule_mode=template.schedule_mode,
        status=template.status,
        store_name=template.store.name if template.store else None,
        doctor_name=template.doctor.name if template.doctor else None,
        department_name=template.department.name if template.department else None,
        created_at=template.created_at,
        updated_at=template.updated_at
    )


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """删除排班模板"""
    service = ScheduleTemplateService(db)
    success = await service.delete(template_id)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    
    return {"message": "删除成功"}


@router.post("/generate")
async def generate_schedules(
    data: ScheduleGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """根据模板批量生成排班"""
    service = ScheduleTemplateService(db)
    
    try:
        created_count = await service.generate_schedules(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return {"message": f"成功创建 {created_count} 条排班", "count": created_count}


@router.post("/batch-add")
async def batch_add_schedules(
    data: ScheduleBatchAddRequest,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """批量添加排班（不依赖模板）"""
    service = ScheduleTemplateService(db)
    
    try:
        created_count = await service.batch_add_schedules(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return {"message": f"成功创建 {created_count} 条排班", "count": created_count}
