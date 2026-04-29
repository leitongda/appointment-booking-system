from fastapi import APIRouter, Depends, HTTPException, Query
from starlette import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import date, timedelta

from app.db.session import get_db
from app.api.deps import get_current_admin, require_permission
from app.schemas.schedule_template import (
    ScheduleTemplateCreate,
    ScheduleTemplateUpdate,
    ScheduleTemplateResponse,
    ScheduleGenerateRequest,
    ScheduleBatchAddRequest,
    SchedulePreviewGenerateRequest,
    SchedulePreviewGenerateResponse,
    ScheduleSlotPreview,
    ScheduleGenerateWithCapacityRequest,
    ScheduleTemplateCopyRequest,
    ScheduleTemplateCopyResponse,
    ScheduleTemplateCrossStoreCopyRequest,
    ScheduleTemplateCrossStoreCopyResponse,
    BreakTime,
)
from app.schemas.schedule_generation_log import (
    ScheduleGenerationLogResponse,
    CheckGeneratedResponse,
    BatchOperateRequest,
    BatchOperateResponse,
)
from app.schemas.response import PageResponse
from app.modules.schedule_templates.service import ScheduleTemplateService
from datetime import time as time_type
from app.core.config import settings

router = APIRouter()


def parse_break_times_for_response(break_times_list: list) -> list:
    """将 break_times_list 转换为 BreakTime 对象列表"""
    if not break_times_list:
        return None
    
    result = []
    for bt in break_times_list:
        try:
            start_key = "startTime" if "startTime" in bt else "start_time"
            end_key = "endTime" if "endTime" in bt else "end_time"
            
            start_val = bt.get(start_key)
            end_val = bt.get(end_key)
            
            # 如果是字符串，转换为 time 对象
            if isinstance(start_val, str):
                parts = start_val.split(":")
                start_time = time_type(int(parts[0]), int(parts[1]))
            elif isinstance(start_val, time_type):
                start_time = start_val
            else:
                continue
            
            if isinstance(end_val, str):
                parts = end_val.split(":")
                end_time = time_type(int(parts[0]), int(parts[1]))
            elif isinstance(end_val, time_type):
                end_time = end_val
            else:
                continue
            
            result.append(BreakTime(start_time=start_time, end_time=end_time))
        except (ValueError, KeyError, TypeError):
            continue
    
    return result if result else None


@router.get("", response_model=PageResponse[ScheduleTemplateResponse], summary="获取列表")
async def get_templates(
    store_id: Optional[str] = None,
    doctor_id: Optional[str] = None,
    department_id: Optional[str] = None,
    status: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
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
                
                # 安全地获取 break_times_list
                break_times = None
                try:
                    if hasattr(t, 'break_times_list'):
                        break_times = parse_break_times_for_response(t.break_times_list)
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
                    break_times=break_times,
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
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取排班模板列表失败: {str(e)}"
        )


@router.get("/{template_id}", response_model=ScheduleTemplateResponse, summary="获取详情")
async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
    """获取排班模板详情"""
    service = ScheduleTemplateService(db)
    template = await service.get_by_id(template_id)
    
    if not template:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="排班模板不存在，请检查后重试")
    
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
        break_times=parse_break_times_for_response(template.break_times_list),
        status=template.status,
        store_name=template.store.name if template.store else None,
        doctor_name=template.doctor.name if template.doctor else None,
        department_name=template.department.name if template.department else None,
        created_at=template.created_at,
        updated_at=template.updated_at
    )


@router.post("", response_model=ScheduleTemplateResponse, summary="创建模板")
async def create_template(
    data: ScheduleTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:create"))
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
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"创建排班模板时发生未知错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"创建失败: {str(e)}")
    
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
        break_times=parse_break_times_for_response(template.break_times_list),
        status=template.status,
        store_name=template.store.name if template.store else None,
        doctor_name=template.doctor.name if template.doctor else None,
        department_name=template.department.name if template.department else None,
        created_at=template.created_at,
        updated_at=template.updated_at
    )


@router.put("/{template_id}", response_model=ScheduleTemplateResponse, summary="更新模板")
async def update_template(
    template_id: str,
    data: ScheduleTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:update"))
):
    """更新排班模板"""
    service = ScheduleTemplateService(db)
    
    try:
        template = await service.update(template_id, data)
    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    if not template:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="排班模板不存在，请检查后重试")
    
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
        break_times=parse_break_times_for_response(template.break_times_list),
        status=template.status,
        store_name=template.store.name if template.store else None,
        doctor_name=template.doctor.name if template.doctor else None,
        department_name=template.department.name if template.department else None,
        created_at=template.created_at,
        updated_at=template.updated_at
    )


@router.delete("/{template_id}", summary="删除模板")
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:delete"))
):
    """删除排班模板"""
    service = ScheduleTemplateService(db)
    success = await service.delete(template_id)
    
    if not success:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="排班模板不存在，请检查后重试")
    
    return {"message": "删除成功"}


WEEKDAY_NAMES = {
    1: "周一",
    2: "周二",
    3: "周三",
    4: "周四",
    5: "周五",
    6: "周六",
    7: "周日",
}


@router.post("/preview-generate", response_model=List[SchedulePreviewGenerateResponse], summary="预览生成")
async def preview_generate_schedules(
    data: SchedulePreviewGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:create"))
):
    """预览生成排班（不实际写入数据库）"""
    from app.utils.schedule_utils import (
        split_time_range_with_breaks,
        get_time_slot_from_time,
        get_period_name_from_time,
        should_generate_schedule,
        calculate_working_duration,
    )
    from app.modules.settings.service import SettingsService
    from app.modules.schedules.service import ScheduleService

    service = ScheduleTemplateService(db)
    settings_service = SettingsService(db)
    schedule_service = ScheduleService(db)

    # 处理日期默认值
    start_date = data.start_date if data.start_date else date.today()
    end_date = data.end_date if data.end_date else start_date + timedelta(days=30)

    results = []

    for template_id in data.template_ids:
        template = await service.get_by_id(template_id)
        if not template or template.status != 1:
            continue

        # 获取星期列表
        weekdays = template.weekday_list
        if not weekdays:
            continue

        # 获取门店的时段配置
        time_periods = await settings_service.get_time_periods(store_id=template.store_id)

        # 获取排除时间列表
        break_times = template.break_times_list or []

        # 计算每日有效工作时长
        daily_duration = calculate_working_duration(
            template.start_time,
            template.end_time,
            break_times
        )
        daily_hours = daily_duration // 60
        daily_minutes = daily_duration % 60

        # 规则引擎校验（模板级别，所有槽位共享）
        rule_warnings = await schedule_service.validate_template_rules(
            shift_type_id=template.shift_type_id if hasattr(template, 'shift_type_id') else None,
            slot_capacity=template.slot_capacity,
            store_id=template.store_id,
            department_id=template.department_id if hasattr(template, 'department_id') else None,
            doctor_id=template.doctor_id,
        )

        # 均分时间生成多个班次
        time_slots = split_time_range_with_breaks(
            template.start_time,
            template.end_time,
            template.slot_count,
            break_times
        )

        slots = []
        current_date = start_date

        while current_date <= end_date:
            weekday = current_date.isoweekday()

            if weekday in weekdays:
                if should_generate_schedule(current_date, template.schedule_mode):
                    for slot_start, slot_end in time_slots:
                        time_slot = get_time_slot_from_time(slot_start, time_periods)
                        period_name = get_period_name_from_time(slot_start, time_periods)
                        slots.append(ScheduleSlotPreview(
                            schedule_date=current_date,
                            start_time=slot_start,
                            end_time=slot_end,
                            time_slot=time_slot,
                            period_name=period_name,
                            slot_capacity=template.slot_capacity,
                            weekday=weekday,
                            weekday_name=WEEKDAY_NAMES.get(weekday, f"星期{weekday}"),
                            rule_validation=rule_warnings if rule_warnings else None,
                        ))

            current_date += timedelta(days=1)

        results.append(SchedulePreviewGenerateResponse(
            slots=slots,
            total_count=len(slots),
            template_id=template.id,
            template_name=template.name,
            doctor_name=template.doctor.name if template.doctor else None,
            department_name=template.department.name if template.department else None,
            daily_duration_hours=daily_hours,
            daily_duration_minutes=daily_minutes
        ))

    return results


@router.post("/generate-with-capacity", summary="批量生成")
async def generate_schedules_with_capacity(
    data: ScheduleGenerateWithCapacityRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:create"))
):
    """根据模板批量生成排班（支持自定义班次容量）"""
    service = ScheduleTemplateService(db)
    
    # 处理日期默认值
    start_date = data.start_date if data.start_date else date.today()
    end_date = data.end_date if data.end_date else start_date + timedelta(days=365)
    
    # 获取操作人信息
    operator_id = current_admin.get("id") if current_admin else None
    operator_name = current_admin.get("username") if current_admin else None
    
    # 构建容量覆盖映射
    capacity_overrides = {}
    if data.slot_capacities:
        for override in data.slot_capacities:
            key = (
                override.schedule_date.isoformat(),
                override.start_time.strftime("%H:%M"),
                override.end_time.strftime("%H:%M")
            )
            capacity_overrides[key] = override.slot_capacity
    
    try:
        created_count = await service.generate_schedules_with_capacity(
            template_ids=data.template_ids,
            start_date=start_date,
            end_date=end_date,
            capacity_overrides=capacity_overrides
        )
        
        # 记录生成日志
        if created_count > 0:
            for template_id in data.template_ids:
                await service.log_generation(
                    template_id=template_id,
                    action_type="generate",
                    affected_count=created_count,
                    operator_id=operator_id,
                    operator_name=operator_name,
                    start_date=start_date,
                    end_date=end_date,
                    remark=f"生成排班（含自定义容量）{created_count} 条"
                )
    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return {"message": f"成功创建 {created_count} 条排班", "count": created_count}


@router.post("/generate", summary="批量生成")
async def generate_schedules(
    data: ScheduleGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:create"))
):
    """根据模板批量生成排班"""
    service = ScheduleTemplateService(db)
    
    # 处理日期默认值
    start_date = data.start_date if data.start_date else date.today()
    end_date = data.end_date if data.end_date else start_date + timedelta(days=365)
    
    # 更新 data 对象中的日期
    data.start_date = start_date
    data.end_date = end_date
    
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
                    start_date=start_date,
                    end_date=end_date,
                    remark=f"生成排班 {created_count} 条"
                )
    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return {"message": f"成功创建 {created_count} 条排班", "count": created_count}


@router.post("/batch-add", summary="批量添加")
async def batch_add_schedules(
    data: ScheduleBatchAddRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:create"))
):
    """批量添加排班（不依赖模板）"""
    service = ScheduleTemplateService(db)
    
    try:
        created_count = await service.batch_add_schedules(data)
    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return {"message": f"成功创建 {created_count} 条排班", "count": created_count}


@router.get("/{template_id}/check-generated", response_model=CheckGeneratedResponse, summary="检查生成")
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
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="排班规则不存在")
    
    return await service.check_generated(template_id, start_date, end_date)


@router.post("/{template_id}/batch-delete", response_model=BatchOperateResponse, summary="批量删除")
async def batch_delete_schedules(
    template_id: str,
    data: Optional[BatchOperateRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:delete"))
):
    """批量删除规则生成的排班"""
    service = ScheduleTemplateService(db)
    
    # 先检查模板是否存在
    template = await service.get_by_id(template_id)
    if not template:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="排班规则不存在")
    
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
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return BatchOperateResponse(
        success=True,
        affected_count=affected_count,
        message=f"成功删除 {affected_count} 条排班记录"
    )


@router.post("/{template_id}/batch-suspend", response_model=BatchOperateResponse, summary="批量停诊")
async def batch_suspend_schedules(
    template_id: str,
    data: Optional[BatchOperateRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:update"))
):
    """批量停诊规则生成的排班"""
    service = ScheduleTemplateService(db)
    
    # 先检查模板是否存在
    template = await service.get_by_id(template_id)
    if not template:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="排班规则不存在")
    
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
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return BatchOperateResponse(
        success=True,
        affected_count=affected_count,
        message=f"成功停诊 {affected_count} 条排班记录"
    )


@router.get("/{template_id}/logs", response_model=PageResponse[ScheduleGenerationLogResponse], summary="获取历史")
async def get_generation_logs(
    template_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取规则的生成历史记录"""
    service = ScheduleTemplateService(db)
    
    # 先检查模板是否存在
    template = await service.get_by_id(template_id)
    if not template:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="排班规则不存在")
    
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


@router.post("/{template_id}/copy", response_model=ScheduleTemplateCopyResponse, summary="复制规则")
async def copy_template_to_doctors(
    template_id: str,
    data: ScheduleTemplateCopyRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:create"))
):
    """复制排班规则给其他医生
    
    将指定规则的配置复制给其他医生，支持在复制时调整配置。
    """
    service = ScheduleTemplateService(db)
    
    # 先检查模板是否存在
    template = await service.get_by_id(template_id)
    if not template:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="排班规则不存在")
    
    # 构建覆盖配置
    overrides = {}
    if data.name is not None:
        overrides['name'] = data.name
    if data.weekdays is not None:
        overrides['weekdays'] = data.weekdays
    if data.appointment_type is not None:
        overrides['appointment_type'] = data.appointment_type
    if data.start_time is not None:
        overrides['start_time'] = data.start_time
    if data.end_time is not None:
        overrides['end_time'] = data.end_time
    if data.slot_count is not None:
        overrides['slot_count'] = data.slot_count
    if data.slot_capacity is not None:
        overrides['slot_capacity'] = data.slot_capacity
    if data.schedule_mode is not None:
        overrides['schedule_mode'] = data.schedule_mode
    if data.break_times is not None:
        overrides['break_times'] = data.break_times
    
    try:
        created_count = await service.copy_to_doctors(
            template_id=template_id,
            target_doctor_ids=data.target_doctor_ids,
            overrides=overrides if overrides else None
        )
    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return ScheduleTemplateCopyResponse(
        message=f"成功复制 {created_count} 条规则",
        created_count=created_count
    )


@router.post("/{template_id}/copy-cross-store", response_model=ScheduleTemplateCrossStoreCopyResponse, summary="跨院区复制规则")
async def copy_template_cross_store(
    template_id: str,
    data: ScheduleTemplateCrossStoreCopyRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:create"))
):
    """跨院区复制排班规则

    将指定规则复制到目标门店，支持科室/医生映射和配置调整。
    """
    service = ScheduleTemplateService(db)

    # 先检查模板是否存在
    template = await service.get_by_id(template_id)
    if not template:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="排班规则不存在")

    # 构建覆盖配置
    overrides = {}
    if data.name is not None:
        overrides['name'] = data.name
    if data.weekdays is not None:
        overrides['weekdays'] = data.weekdays
    if data.appointment_type is not None:
        overrides['appointment_type'] = data.appointment_type
    if data.start_time is not None:
        overrides['start_time'] = data.start_time
    if data.end_time is not None:
        overrides['end_time'] = data.end_time
    if data.slot_count is not None:
        overrides['slot_count'] = data.slot_count
    if data.slot_capacity is not None:
        overrides['slot_capacity'] = data.slot_capacity
    if data.schedule_mode is not None:
        overrides['schedule_mode'] = data.schedule_mode
    if data.break_times is not None:
        overrides['break_times'] = data.break_times

    try:
        created_count, failed_mappings = await service.copy_to_store(
            template_id=template_id,
            target_store_id=data.target_store_id,
            mappings=[m.model_dump() for m in data.mappings],
            overrides=overrides if overrides else None
        )
    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(e))

    message = f"成功复制 {created_count} 条规则"
    if failed_mappings:
        message += f"，{len(failed_mappings)} 条映射失败"

    return ScheduleTemplateCrossStoreCopyResponse(
        message=message,
        created_count=created_count,
        failed_mappings=failed_mappings if failed_mappings else None
    )
