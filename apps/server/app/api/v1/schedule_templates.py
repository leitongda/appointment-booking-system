from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.schemas.schedule_template import (
    ScheduleTemplateCreate,
    ScheduleTemplateUpdate,
    ScheduleTemplateResponse,
    ScheduleGenerateRequest,
    ScheduleBatchAddRequest,
)
from app.schemas.schedule_generation_log import (
    ScheduleGenerationLogResponse,
    CheckGeneratedResponse,
    BatchOperateRequest,
    BatchOperateResponse,
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
    import logging
    logger = logging.getLogger(__name__)
    
    try:
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
            try:
                # 安全地获取 weekday_list
                weekdays = []
                try:
                    weekdays = t.weekday_list if hasattr(t, 'weekday_list') else []
                except Exception as e:
                    logger.warning(f"获取模板 {t.id} 的 weekday_list 失败: {str(e)}")
                    weekdays = []
                
                # 安全地获取关联对象名称
                store_name = None
                try:
                    if t.store and hasattr(t.store, 'name'):
                        store_name = t.store.name
                except Exception:
                    pass
                
                doctor_name = None
                try:
                    if t.doctor and hasattr(t.doctor, 'name'):
                        doctor_name = t.doctor.name
                except Exception:
                    pass
                
                department_name = None
                try:
                    if t.department and hasattr(t.department, 'name'):
                        department_name = t.department.name
                except Exception:
                    pass
                
                result.append(ScheduleTemplateResponse(
                    id=t.id,
                    name=t.name,
                    store_id=t.store_id,
                    doctor_id=t.doctor_id,
                    department_id=t.department_id,
                    weekdays=weekdays,
                    appointment_type=t.appointment_type,
                    start_time=t.start_time,
                    end_time=t.end_time,
                    slot_count=t.slot_count,
                    slot_capacity=t.slot_capacity,
                    schedule_mode=t.schedule_mode,
                    status=t.status,
                    store_name=store_name,
                    doctor_name=doctor_name,
                    department_name=department_name,
                    created_at=t.created_at,
                    updated_at=t.updated_at
                ))
            except Exception as e:
                logger.error(f"处理模板 {t.id if t else 'unknown'} 时出错: {str(e)}", exc_info=True)
                # 跳过有问题的模板，继续处理其他模板
                continue
        
        return PageResponse(data=result, total=total, page=page, page_size=page_size)
    except Exception as e:
        logger.error(f"获取排班模板列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取排班模板列表失败: {str(e)}"
        )


@router.get("/{template_id}", response_model=ScheduleTemplateResponse)
async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
    """获取排班模板详情"""
    service = ScheduleTemplateService(db)
    template = await service.get_by_id(template_id)
    
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排班模板不存在，请检查后重试")
    
    return ScheduleTemplateResponse(
        id=template.id,
        name=template.name,
        store_id=template.store_id,
        doctor_id=template.doctor_id,
        department_id=template.department_id,
        weekdays=template.weekday_list,
        appointment_type=template.appointment_type,
        start_time=template.start_time,
        end_time=template.end_time,
        slot_count=template.slot_count,
        slot_capacity=template.slot_capacity,
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
    import logging
    logger = logging.getLogger(__name__)
    
    # 记录接收到的数据（用于调试）
    logger.info(f"创建排班模板，数据: name={data.name}, store_id={data.store_id}, "
                f"doctor_id={data.doctor_id}, department_id={data.department_id}, "
                f"start_time={data.start_time} (type: {type(data.start_time)}), "
                f"end_time={data.end_time} (type: {type(data.end_time)}), "
                f"slot_count={data.slot_count}, slot_capacity={data.slot_capacity}")
    
    service = ScheduleTemplateService(db)
    
    try:
        template = await service.create(data)
    except ValueError as e:
        logger.error(f"创建排班模板失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"创建排班模板时发生未知错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"创建失败: {str(e)}")
    
    # 重新加载关联数据
    template = await service.get_by_id(template.id)
    
    return ScheduleTemplateResponse(
        id=template.id,
        name=template.name,
        store_id=template.store_id,
        doctor_id=template.doctor_id,
        department_id=template.department_id,
        weekdays=template.weekday_list,
        appointment_type=template.appointment_type,
        start_time=template.start_time,
        end_time=template.end_time,
        slot_count=template.slot_count,
        slot_capacity=template.slot_capacity,
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排班模板不存在，请检查后重试")
    
    # 重新加载关联数据
    template = await service.get_by_id(template.id)
    
    return ScheduleTemplateResponse(
        id=template.id,
        name=template.name,
        store_id=template.store_id,
        doctor_id=template.doctor_id,
        department_id=template.department_id,
        weekdays=template.weekday_list,
        appointment_type=template.appointment_type,
        start_time=template.start_time,
        end_time=template.end_time,
        slot_count=template.slot_count,
        slot_capacity=template.slot_capacity,
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排班模板不存在，请检查后重试")
    
    return {"message": "删除成功"}


@router.post("/generate")
async def generate_schedules(
    data: ScheduleGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """根据模板批量生成排班"""
    service = ScheduleTemplateService(db)
    
    # 获取操作人信息
    operator_id = current_admin.get("id") if current_admin else None
    operator_name = current_admin.get("username") if current_admin else None
    
    try:
        created_count = await service.generate_schedules(data)
        
        # 记录生成日志
        if created_count > 0:
            for template_id in data.template_ids:
                await service.log_generation(
                    template_id=template_id,
                    action_type="generate",
                    affected_count=created_count,
                    operator_id=operator_id,
                    operator_name=operator_name,
                    start_date=data.start_date,
                    end_date=data.end_date,
                    remark=f"生成排班 {created_count} 条"
                )
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


@router.get("/{template_id}/check-generated", response_model=CheckGeneratedResponse)
async def check_generated(
    template_id: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """检查规则是否已生成过排班"""
    service = ScheduleTemplateService(db)
    
    # 先检查模板是否存在
    template = await service.get_by_id(template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排班规则不存在")
    
    return await service.check_generated(template_id, start_date, end_date)


@router.post("/{template_id}/batch-delete", response_model=BatchOperateResponse)
async def batch_delete_schedules(
    template_id: str,
    data: Optional[BatchOperateRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """批量删除规则生成的排班"""
    service = ScheduleTemplateService(db)
    
    # 先检查模板是否存在
    template = await service.get_by_id(template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排班规则不存在")
    
    # 获取操作人信息
    operator_id = current_admin.get("id") if current_admin else None
    operator_name = current_admin.get("username") if current_admin else None
    
    # 处理请求参数
    start_date = data.start_date if data else None
    end_date = data.end_date if data else None
    future_only = data.future_only if data else True
    
    try:
        affected_count = await service.batch_delete_schedules(
            template_id=template_id,
            operator_id=operator_id,
            operator_name=operator_name,
            start_date=start_date,
            end_date=end_date,
            future_only=future_only
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return BatchOperateResponse(
        success=True,
        affected_count=affected_count,
        message=f"成功删除 {affected_count} 条排班记录"
    )


@router.post("/{template_id}/batch-suspend", response_model=BatchOperateResponse)
async def batch_suspend_schedules(
    template_id: str,
    data: Optional[BatchOperateRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """批量停诊规则生成的排班"""
    service = ScheduleTemplateService(db)
    
    # 先检查模板是否存在
    template = await service.get_by_id(template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排班规则不存在")
    
    # 获取操作人信息
    operator_id = current_admin.get("id") if current_admin else None
    operator_name = current_admin.get("username") if current_admin else None
    
    # 处理请求参数
    start_date = data.start_date if data else None
    end_date = data.end_date if data else None
    future_only = data.future_only if data else True
    
    try:
        affected_count = await service.batch_suspend_schedules(
            template_id=template_id,
            operator_id=operator_id,
            operator_name=operator_name,
            start_date=start_date,
            end_date=end_date,
            future_only=future_only
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return BatchOperateResponse(
        success=True,
        affected_count=affected_count,
        message=f"成功停诊 {affected_count} 条排班记录"
    )


@router.get("/{template_id}/logs", response_model=PageResponse[ScheduleGenerationLogResponse])
async def get_generation_logs(
    template_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取规则的生成历史记录"""
    service = ScheduleTemplateService(db)
    
    # 先检查模板是否存在
    template = await service.get_by_id(template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排班规则不存在")
    
    logs, total = await service.get_generation_logs(template_id, page, page_size)
    
    result = [
        ScheduleGenerationLogResponse(
            id=log.id,
            template_id=log.template_id,
            operator_id=log.operator_id,
            operator_name=log.operator_name,
            action_type=log.action_type,
            start_date=log.start_date,
            end_date=log.end_date,
            affected_count=log.affected_count,
            remark=log.remark,
            created_at=log.created_at
        )
        for log in logs
    ]
    
    return PageResponse(data=result, total=total, page=page, page_size=page_size)
