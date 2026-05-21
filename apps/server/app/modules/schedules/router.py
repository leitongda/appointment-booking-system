from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, Field
import pytz
import logging

from app.db.session import get_db

logger = logging.getLogger(__name__)
from app.api.deps import get_current_admin, get_store_filter, check_store_access, require_permission
from app.schemas.schedule import (
    ScheduleCreate, ScheduleBatchCreate, ScheduleUpdate, ScheduleResponse,
    AvailableScheduleResponse,
    SchedulePublishRequest, ScheduleWithdrawRequest,
    ConflictCheckRequest, ConflictCheckResponse, ConflictItemResponse,
    ScheduleDragAdjustRequest, ScheduleDragAdjustResponse,
    ScheduleBatchCopyRequest, ScheduleBatchCopyResult,
)
from app.schemas.response import PageResponse
from app.modules.schedules.service import ScheduleService

from app.modules.rule_engine import RuleEngineService
from app.models.schedule import Schedule
from app.models.doctor import Doctor
from app.models.rest_day import RestDay
from app.core.config import settings

router = APIRouter()


class BatchOperateResponse(BaseModel):
    """批量操作响应"""
    success: bool
    affected_count: int
    message: str


async def _check_single_schedule_rest_day(
    db: AsyncSession,
    schedule_date: date,
    store_id: Optional[str],
    doctor_id: str
) -> bool:
    """检查单个排班是否在休息日"""
    from app.utils.schedule_utils import is_rest_day
    rest_day_result = await db.execute(
        select(RestDay).where(
            and_(
                RestDay.status == 1,
                RestDay.start_date <= schedule_date,
                RestDay.end_date >= schedule_date
            )
        )
    )
    rest_days = rest_day_result.scalars().all()
    return is_rest_day(rest_days, schedule_date, store_id, doctor_id)


def _check_rest_day_for_schedule(
    schedule_date: date,
    store_id: Optional[str],
    doctor_id: str,
    rest_days: list
) -> bool:
    """检查指定排班是否在休息日（基于已查询的休息日列表）"""
    from app.utils.schedule_utils import is_rest_day
    return is_rest_day(rest_days, schedule_date, store_id, doctor_id)


class SuspendRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=200, description="停诊原因")
    notify_patients: bool = Field(True, description="是否通知患者")

@router.get(
    "",
    response_model=PageResponse[ScheduleResponse],
    summary="获取排班列表",
    description="""
    获取排班列表（管理端），支持分页和多条件筛选。

    **支持筛选条件**：
    - doctor_id: 按医生筛选
    - store_id: 按门店筛选
    - start_date / end_date: 按排班日期范围筛选
    - status: 按状态筛选（1=正常 0=停诊）

    **数据隔离**：
    - 门店管理员只能查看本门店的排班

    **返回数据**：
    - 包含医生姓名、科室名称等关联信息
    - 包含 is_rest_day 字段，标记该排班日期是否在休息日范围内
    - 休息日判断逻辑：全局休息日 + 门店级休息日 + 医生级休息日
    """,
)
async def get_schedules(
    doctor_id: Optional[str] = None,
    store_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[int] = None,
    schedule_status: Optional[str] = Query(None, description="排班状态: draft/published/booking/full/suspended/finished/withdrawn"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:read"))
):
    """获取排班列表"""
    # 门店过滤
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter

    service = ScheduleService(db)
    schedules, total = await service.get_list(
        doctor_id=doctor_id, store_id=store_id, start_date=start_date, end_date=end_date,
        status=status, schedule_status=schedule_status,
        page=page, page_size=page_size,
    )
    
    # 查询日期范围内的所有有效休息日（用于计算 is_rest_day）
    rest_days = []
    if schedules and (start_date or end_date):
        query_start = start_date or min(s.schedule_date for s in schedules)
        query_end = end_date or max(s.schedule_date for s in schedules)
        rest_day_result = await db.execute(
            select(RestDay).where(
                and_(
                    RestDay.status == 1,
                    RestDay.start_date <= query_end,
                    RestDay.end_date >= query_start
                )
            )
        )
        rest_days = rest_day_result.scalars().all()
    
    def check_rest_day(schedule_date, schedule_store_id, schedule_doctor_id) -> bool:
        """检查指定排班是否在休息日"""
        from app.utils.schedule_utils import is_rest_day
        return is_rest_day(rest_days, schedule_date, schedule_store_id, schedule_doctor_id)
    
    result = []
    for s in schedules:
        is_rest = check_rest_day(s.schedule_date, s.store_id, s.doctor_id)
        result.append(ScheduleResponse(
            id=s.id,
            doctor_id=s.doctor_id,
            store_id=s.store_id,
            doctor_name=s.doctor.name if s.doctor else None,
            department_name=s.doctor.department.name if s.doctor and s.doctor.department else None,
            schedule_date=s.schedule_date,
            time_slot=s.time_slot,
            start_time=s.start_time,
            end_time=s.end_time,
            total_slots=s.total_slots,
            booked_slots=s.booked_slots,
            appointment_type=s.appointment_type,
            template_id=s.template_id,
            status=s.status,
            schedule_status=s.schedule_status,
            created_at=s.created_at,
            is_rest_day=is_rest,
            effective_status=getattr(s, 'effective_status', 'active'),
        ))
    
    return PageResponse(data=result, total=total, page=page, page_size=page_size)




# ========== 排班冲突检测端点 ==========


@router.post(
    "/conflicts",
    response_model=ConflictCheckResponse,
    summary="排班冲突预检",
    description="""
    在创建或编辑排班前进行冲突预检（不保存数据，仅检测）。

    **权限要求**：管理员权限（schedule:read）。

    **检查项**：
    - 医生时间重叠（error）
    - 诊室占用（error，指定诊室时检测）
    - 午休时间覆盖（warning）
    - 节假日限制（error，法定节假日不允许排班时）
    - 休息日冲突（warning）
    - 医生状态（error，离职/禁用）

    **严重级别**：
    - error: 阻止保存
    - warning: 允许保存但前端应提示用户确认
    """,
)
async def check_conflicts(
    data: ConflictCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:read")),
):
    """排班冲突预检"""
    from app.modules.schedules.service_conflict import ScheduleConflictService

    service = ScheduleConflictService(db)
    result = await service.check_conflicts(
        doctor_id=data.doctor_id,
        schedule_date=data.schedule_date,
        start_time=data.start_time,
        end_time=data.end_time,
        time_slot=data.time_slot,
        store_id=data.store_id,
        room_id=data.room_id,
        exclude_schedule_id=data.exclude_schedule_id,
    )

    return ConflictCheckResponse(
        has_conflict=result.has_conflict,
        blocking=result.blocking,
        conflicts=[
            ConflictItemResponse(
                type=c.type,
                severity=c.severity,
                message=c.message,
                details=c.details,
            )
            for c in result.conflicts
        ],
    )


# ========== 排班拖拽调整端点 ==========


@router.post(
    "/drag-adjust",
    summary="拖拽调整排班",
    description="""
    拖拽调整排班的日期和时间（日历拖拽交互专用）。

    **权限要求**：管理员权限（schedule:update）。

    **业务规则**：
    - 已有预约的排班不允许拖拽
    - 停诊状态的排班不允许拖拽
    - 历史排班不允许拖拽
    - 目标位置有 error 级别冲突时返回冲突信息
    - 使用分布式锁防止并发拖拽冲突
    """,
)
async def drag_adjust_schedule(
    data: ScheduleDragAdjustRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:update")),
):
    """拖拽调整排班"""
    service = ScheduleService(db)
    result = await service.drag_adjust(
        schedule_id=data.schedule_id,
        target_date=data.target_date,
        target_start_time=data.target_start_time,
        target_end_time=data.target_end_time,
        target_time_slot=data.target_time_slot,
        operator_id=current_admin.get("id"),
    )

    if not result["success"]:
        if result.get("conflicts"):
            return ScheduleDragAdjustResponse(
                success=False,
                conflicts=result["conflicts"],
                message=result["message"],
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["message"])

    schedule = result["schedule"]
    return ScheduleDragAdjustResponse(
        success=True,
        schedule=ScheduleResponse(
            id=schedule.id,
            doctor_id=schedule.doctor_id,
            store_id=schedule.store_id,
            schedule_date=schedule.schedule_date,
            time_slot=schedule.time_slot,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            total_slots=schedule.total_slots,
            booked_slots=schedule.booked_slots,
            appointment_type=schedule.appointment_type,
            template_id=schedule.template_id,
            status=schedule.status,
            schedule_status=schedule.schedule_status,
            created_at=schedule.created_at,
        ),
        message=result["message"],
    )


@router.get(
    "/available/{doctor_id}",
    response_model=List[AvailableScheduleResponse],
    summary="获取可预约排班",
    description="""
    获取指定医生的可预约排班（公开接口，患者端使用）。

    **参数说明**：
    - doctor_id: 医生ID（路径参数）
    - store_id: 门店ID（可选，用于查询该医生的预约设置）
    - days: 查询未来天数（默认14天，最大30天，当医生有预约设置时作为 fallback）

    **返回数据**：
    - 包含规则引擎计算的预约时间窗信息（booking_open_at / booking_close_at）
    - booking_status: available（可预约）/ not_open（未开放）/ closed（已截止）/ full（约满）/ closing_soon（即将约满）
    - capacity_percent: 剩余容量百分比
    - urgency_level: 紧急程度（normal/medium/high/critical）
    - is_rest_day: 是否在休息日（此处始终为 False，因为已过滤）
    - booking_setting_applied: 是否应用了医生预约设置
    """,
)
async def get_available_schedules(
    doctor_id: str,
    store_id: Optional[str] = Query(None, description="门店ID"),
    days: int = Query(14, ge=1, le=30),
    db: AsyncSession = Depends(get_db)
):
    """获取可预约排班（增强版：包含规则引擎信息）"""
    service = ScheduleService(db)
    rule_engine = RuleEngineService(db)
    schedules, booking_setting_applied = await service.get_available(
        doctor_id, days=days, store_id=store_id
    )

    # 使用本地时区（中国标准时间）
    local_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(local_tz)
    result = []

    for s in schedules:
        available = s.total_slots - s.booked_slots

        # 检查预约时间窗（使用规则引擎）
        booking_open_at = None
        booking_close_at = None
        booking_status = "available"

        try:
            window_check = await rule_engine.check_action_window(s, 'BOOK', now)
            if window_check.get('allowed'):
                booking_open_at = window_check.get('open_at')
                booking_close_at = window_check.get('close_at')
            else:
                # 未开放或已截止
                if now < window_check.get('open_at', now):
                    booking_status = 'not_open'
                    booking_open_at = window_check.get('open_at')
                    booking_close_at = window_check.get('close_at')
                else:
                    booking_status = 'closed'
                    booking_open_at = window_check.get('open_at')
                    booking_close_at = window_check.get('close_at')
        except Exception as e:
            # 规则引擎检查失败，记录日志并使用默认状态
            logger.warning(f"规则引擎检查失败: schedule_id={s.id}, error={e}")

        # 如果已约满，覆盖状态
        if available == 0:
            booking_status = 'full'

        # 计算容量百分比
        capacity_percent = (available / s.total_slots * 100) if s.total_slots > 0 else 0

        # 判断紧急程度（按百分比：>50%正常，20-50%中等，<20%紧急，0%约满）
        urgency_level = "normal"
        if available == 0:
            urgency_level = "critical"  # 约满
        elif capacity_percent < 20:
            urgency_level = "high"
        elif capacity_percent < 50:
            urgency_level = "medium"

        # 如果即将截止（<30分钟），提升紧急程度
        if booking_close_at:
            minutes_until_close = (booking_close_at - now).total_seconds() / 60
            if 0 < minutes_until_close < 30 and booking_status == 'available':
                if urgency_level == 'normal':
                    urgency_level = 'medium'
                elif urgency_level == 'medium':
                    urgency_level = 'high'

        # 更新即将约满状态
        if booking_status == 'available' and capacity_percent < 30 and capacity_percent > 0:
            booking_status = 'closing_soon'

        # 自定义排班（template_id=None）不受休息日影响，is_rest_day 始终为 False
        # 这里的排班已经通过 get_available 过滤，所以能到这里的要么不是休息日，
        # 要么是自定义排班（不受休息日影响）
        is_rest_day_flag = False  # 已过滤，这里的排班都是可预约的

        result.append(AvailableScheduleResponse(
            id=s.id,
            schedule_date=s.schedule_date,
            time_slot=s.time_slot,
            available_slots=available,
            total_slots=s.total_slots,
            start_time=s.start_time,
            end_time=s.end_time,
            appointment_type=s.appointment_type,
            booking_open_at=booking_open_at,
            booking_close_at=booking_close_at,
            booking_status=booking_status,
            capacity_percent=round(capacity_percent, 1),
            urgency_level=urgency_level,
            template_id=s.template_id,
            is_rest_day=is_rest_day_flag,
            booking_setting_applied=booking_setting_applied,
        ))

    return result


# ========== 子路由注册（必须在 /{schedule_id} 之前，否则静态路径被参数路由吞掉） ==========
from app.modules.schedules.router_statistics import router as statistics_router
from app.modules.schedules.router_extra_quota import router as extra_quota_router
from app.modules.schedules.router_custom import router as custom_router

router.include_router(statistics_router)
router.include_router(extra_quota_router)
router.include_router(custom_router)


@router.get(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    summary="获取排班详情",
    description="""
    获取排班详情（管理端接口）。

    **参数说明**：
    - schedule_id: 排班记录ID（路径参数）

    **返回数据**：
    - 包含医生姓名、科室名称等关联信息
    - 包含 is_rest_day 字段，通过休息日配置判断
    """,
)
async def get_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:read"))
):
    """获取排班详情"""
    service = ScheduleService(db)
    schedule = await service.get_by_id(schedule_id)
    
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排班不存在，请检查后重试")
    
    # 检查是否在休息日
    is_rest_day = await _check_single_schedule_rest_day(
        db, schedule.schedule_date, schedule.store_id, schedule.doctor_id
    )
    
    return ScheduleResponse(
        id=schedule.id,
        doctor_id=schedule.doctor_id,
        store_id=schedule.store_id,
        doctor_name=schedule.doctor.name if schedule.doctor else None,
        department_name=schedule.doctor.department.name if schedule.doctor and schedule.doctor.department else None,
        schedule_date=schedule.schedule_date,
        time_slot=schedule.time_slot,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        total_slots=schedule.total_slots,
        booked_slots=schedule.booked_slots,
        appointment_type=schedule.appointment_type,
        template_id=schedule.template_id,
        status=schedule.status,
        schedule_status=schedule.schedule_status,
        created_at=schedule.created_at,
        is_rest_day=is_rest_day
    )

@router.post(
    "",
    response_model=ScheduleResponse,
    summary="创建排班",
    description="""
    创建单条排班记录。

    **权限要求**：管理员权限（schedule:create）。

    **业务规则**：
    - 同一医生同一天同一时段不可重复排班
    - 需指定医生（doctor_id）、排班日期（schedule_date）、时段（time_slot）、号源数量（total_slots）
    - 创建后自动检查是否与休息日冲突，返回 is_rest_day 标记
    """,
)
async def create_schedule(
    data: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:create"))
):
    """创建排班"""
    service = ScheduleService(db)
    
    try:
        schedule = await service.create(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    # 检查是否在休息日
    is_rest_day = await _check_single_schedule_rest_day(
        db, schedule.schedule_date, schedule.store_id, schedule.doctor_id
    )
    
    return ScheduleResponse(
        id=schedule.id,
        doctor_id=schedule.doctor_id,
        store_id=schedule.store_id,
        schedule_date=schedule.schedule_date,
        time_slot=schedule.time_slot,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        total_slots=schedule.total_slots,
        booked_slots=schedule.booked_slots,
        appointment_type=schedule.appointment_type,
        template_id=schedule.template_id,
        status=schedule.status,
        schedule_status=schedule.schedule_status,
        created_at=schedule.created_at,
        is_rest_day=is_rest_day
    )

@router.post(
    "/batch",
    response_model=BatchOperateResponse,
    summary="批量创建排班",
    description="""
    批量创建排班记录，支持按日期范围和医生列表批量生成。

    **权限要求**：管理员权限（schedule:create）。

    **业务规则**：
    - 自动跳过已存在排班的日期/时段（不报错）
    - 休息日内的排班会自动跳过
    - 返回实际创建的排班数量（affected_count）
    """,
)
async def batch_create_schedules(
    data: ScheduleBatchCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:create"))
):
    """批量创建排班"""
    service = ScheduleService(db)
    try:
        created_count = await service.batch_create(data, operator_id=current_admin.get("id"))
        return BatchOperateResponse(
            success=True,
            affected_count=created_count,
            message=f"成功创建 {created_count} 条排班"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    summary="更新排班",
    description="""
    更新排班信息。

    **权限要求**：管理员权限（schedule:update）。

    **业务规则**：
    - 已有预约记录的排班，号源数量不可少于已预约数量（booked_slots）
    - 更新后自动检查休息日冲突

    **参数说明**：
    - schedule_id: 排班记录ID（路径参数）
    """,
)
async def update_schedule(
    schedule_id: str,
    data: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:update"))
):
    """更新排班"""
    service = ScheduleService(db)
    
    try:
        schedule = await service.update(schedule_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排班不存在，请检查后重试")
    
    # 检查是否在休息日
    is_rest_day = await _check_single_schedule_rest_day(
        db, schedule.schedule_date, schedule.store_id, schedule.doctor_id
    )
    
    return ScheduleResponse(
        id=schedule.id,
        doctor_id=schedule.doctor_id,
        store_id=schedule.store_id,
        schedule_date=schedule.schedule_date,
        time_slot=schedule.time_slot,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        total_slots=schedule.total_slots,
        booked_slots=schedule.booked_slots,
        appointment_type=schedule.appointment_type,
        template_id=schedule.template_id,
        status=schedule.status,
        schedule_status=schedule.schedule_status,
        created_at=schedule.created_at,
        is_rest_day=is_rest_day
    )

class BatchScheduleRequest(BaseModel):
    """批量操作排班请求"""
    schedule_ids: List[str] = Field(..., min_length=1, description="排班ID列表")
    reason: Optional[str] = Field(None, max_length=200, description="操作原因")
    processing_method: Optional[str] = Field(
        None,
        description="处置方式（仅批量停诊有效）: auto_refund/reschedule/change_date/manual",
    )


@router.post(
    "/batch-suspend",
    response_model=BatchOperateResponse,
    summary="批量停诊",
    description="""
    批量将排班标记为停诊状态。

    **权限要求**：管理员权限（schedule:update）。

    **业务规则**：
    - 停诊后对应排班不再对患者可见
    - 已有预约的处理由 service 层决定（通知患者等）
    - 返回实际影响的排班数量

    **参数说明**：
    - schedule_ids: 排班ID列表（必填，至少1个）
    - reason: 停诊原因（可选，最大200字）
    """,
)
async def batch_suspend_schedules(
    data: BatchScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:suspend"))
):
    """批量停诊排班"""
    service = ScheduleService(db)

    try:
        result = await service.batch_suspend(
            data.schedule_ids,
            data.reason,
            operator_id=current_admin.get("id"),
            processing_method=data.processing_method,
        )
        return BatchOperateResponse(
            success=True,
            affected_count=result["success_count"],
            message=result["message"]
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/batch-resume",
    response_model=BatchOperateResponse,
    summary="批量恢复排班",
    description="""
    批量恢复已停诊的排班。

    **权限要求**：管理员权限（schedule:update）。

    **业务规则**：
    - 恢复后排班重新对患者可见
    - 只有已停诊状态的排班会受影响
    - 返回实际恢复的排班数量

    **参数说明**：
    - schedule_ids: 排班ID列表（必填，至少1个）
    """,
)
async def batch_resume_schedules(
    data: BatchScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:suspend"))
):
    """批量恢复排班"""
    service = ScheduleService(db)

    try:
        affected_count = await service.batch_resume(
            data.schedule_ids,
            operator_id=current_admin.get("id")
        )
        return BatchOperateResponse(
            success=True,
            affected_count=affected_count,
            message=f"成功恢复 {affected_count} 条排班记录"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/batch-delete",
    response_model=BatchOperateResponse,
    summary="批量删除排班",
    description="""
    批量删除排班记录。

    **权限要求**：管理员权限（schedule:delete）。

    **业务规则**：
    - 只能删除没有任何预约记录的排班
    - 存在预约记录的排班会自动跳过（不报错）
    - 返回消息中包含实际删除数量和跳过数量

    **参数说明**：
    - schedule_ids: 排班ID列表（必填，至少1个）
    """,
)
async def batch_delete_schedules(
    data: BatchScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:delete"))
):
    """批量删除排班（只能删除没有任何预约记录的排班）"""
    service = ScheduleService(db)
    
    try:
        result = await service.batch_delete(data.schedule_ids)
        affected_count = result.get("deleted_count", 0)
        skipped_ids = result.get("skipped_ids", [])
        message = f"成功删除 {affected_count} 条排班记录"
        if skipped_ids:
            message += f"，{len(skipped_ids)} 条因存在预约记录而跳过"
        return BatchOperateResponse(
            success=True,
            affected_count=affected_count,
            message=message
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ========== 排班发布状态机端点 ==========


@router.post(
    "/{schedule_id}/publish",
    response_model=ScheduleResponse,
    summary="发布排班",
    description="""
    发布单条排班（draft -> published）。

    **权限要求**：管理员权限（schedule:update）。

    **业务规则**：
    - 只有 draft 状态的排班可以发布
    - 发布后排班对患者可见（需同时满足其他预约条件）
    """,
)
async def publish_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:update")),
):
    """发布排班"""
    service = ScheduleService(db)
    try:
        schedule = await service.publish(schedule_id, operator_id=current_admin.get("id"))
        return ScheduleResponse(
            id=schedule.id,
            doctor_id=schedule.doctor_id,
            store_id=schedule.store_id,
            doctor_name=schedule.doctor.name if schedule.doctor else None,
            department_name=schedule.doctor.department.name if schedule.doctor and schedule.doctor.department else None,
            schedule_date=schedule.schedule_date,
            time_slot=schedule.time_slot,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            total_slots=schedule.total_slots,
            booked_slots=schedule.booked_slots,
            appointment_type=schedule.appointment_type,
            template_id=schedule.template_id,
            status=schedule.status,
            schedule_status=schedule.schedule_status,
            created_at=schedule.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/batch-publish",
    response_model=BatchOperateResponse,
    summary="批量发布排班",
    description="""
    批量发布排班（draft -> published）。

    **权限要求**：管理员权限（schedule:update）。

    **业务规则**：
    - 只有 draft 状态的排班会被发布
    - 非 draft 状态的排班会记录在 failed_items 中
    """,
)
async def batch_publish_schedules(
    data: SchedulePublishRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:update")),
):
    """批量发布排班"""
    service = ScheduleService(db)
    try:
        result = await service.batch_publish(
            data.schedule_ids,
            operator_id=current_admin.get("id"),
        )
        return BatchOperateResponse(
            success=True,
            affected_count=result["success_count"],
            message=result["message"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/batch-withdraw",
    response_model=BatchOperateResponse,
    summary="批量撤回排班",
    description="""
    批量撤回排班（published/booking -> withdrawn）。

    **权限要求**：管理员权限（schedule:update）。

    **业务规则**：
    - 只有 published 或 booking 状态的排班可以撤回
    - 存在活跃预约（待支付/已预约/已签到/就诊中）的排班无法撤回
    - 撤回后排班对患者不可见
    """,
)
async def batch_withdraw_schedules(
    data: ScheduleWithdrawRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:update")),
):
    """批量撤回排班"""
    service = ScheduleService(db)
    try:
        result = await service.withdraw(
            data.schedule_ids,
            reason=data.reason,
            operator_id=current_admin.get("id"),
        )
        return BatchOperateResponse(
            success=True,
            affected_count=result["success_count"],
            message=result["message"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/copy",
    response_model=ScheduleBatchCopyResult,
    summary="批量复制排班",
    description="""
    将源周期的排班批量复制到目标周期。

    **权限要求**：管理员权限（schedule:create）。

    **业务规则**：
    - 源周期和目标周期的天数应匹配（自动按日期偏移）
    - 支持按医生筛选（doctor_ids 为空则复制全部）
    - copy_quota/copy_room/copy_fee 控制是否复制对应配置
    - skip_holidays 跳过节假日和休息日
    - conflict_strategy 处理目标位置已有排班的冲突：
      - skip: 跳过冲突项
      - overwrite: 删除旧排班后覆盖（仅限无预约的排班）
      - manual: 收集冲突信息返回，由调用方决策
    - 使用分布式锁保护，防止并发冲突
    """,
)
async def batch_copy_schedules(
    data: ScheduleBatchCopyRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:create")),
):
    """批量复制排班"""
    service = ScheduleService(db)

    try:
        result = await service.batch_copy(data, operator_id=current_admin.get("id"))
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
