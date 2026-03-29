from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract
from typing import Optional, List
from datetime import date, datetime, timezone
from calendar import monthrange
from pydantic import BaseModel, Field
import pytz
import logging

from app.db.session import get_db

logger = logging.getLogger(__name__)
from app.api.deps import get_current_admin, get_store_filter, check_store_access, require_permission
from app.schemas.schedule import ScheduleCreate, ScheduleBatchCreate, ScheduleUpdate, ScheduleResponse, AvailableScheduleResponse
from app.schemas.response import PageResponse
from app.modules.schedules.service import ScheduleService
from app.infrastructure.notification.service import NotificationService
from app.modules.rule_engine import RuleEngineService
from app.models.schedule import Schedule
from app.models.doctor import Doctor
from app.models.store import Store
from app.models.rest_day import RestDay
from app.core.config import settings
import json

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
    
    for rd in rest_days:
        # 检查门店是否匹配
        if store_id and rd.store_id != store_id:
            continue
        # 如果 doctor_ids 为空，表示门店所有医生休息
        if rd.doctor_ids is None:
            return True
        # 检查医生是否在休息日列表中
        try:
            doctor_ids_list = json.loads(rd.doctor_ids)
            if doctor_id in doctor_ids_list:
                return True
        except:
            pass
    return False


class SuspendRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=200, description="停诊原因")
    notify_patients: bool = Field(True, description="是否通知患者")

@router.get("", response_model=PageResponse[ScheduleResponse], summary="获取排班列表")
async def get_schedules(
    doctor_id: Optional[str] = None,
    store_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取排班列表"""
    # 门店过滤
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter
    
    service = ScheduleService(db)
    schedules, total = await service.get_list(
        doctor_id=doctor_id, store_id=store_id, start_date=start_date, end_date=end_date,
        status=status, page=page, page_size=page_size
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
        for rd in rest_days:
            # 检查日期是否在休息日范围内
            if not (rd.start_date <= schedule_date <= rd.end_date):
                continue
            # 检查门店是否匹配
            if schedule_store_id and rd.store_id != schedule_store_id:
                continue
            # 如果 doctor_ids 为空，表示门店所有医生休息
            if rd.doctor_ids is None:
                return True
            # 检查医生是否在休息日列表中
            try:
                doctor_ids_list = json.loads(rd.doctor_ids)
                if schedule_doctor_id in doctor_ids_list:
                    return True
            except:
                pass
        return False
    
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
            created_at=s.created_at,
            is_rest_day=is_rest
        ))
    
    return PageResponse(data=result, total=total, page=page, page_size=page_size)


class ScheduleStatisticsItem(BaseModel):
    """排班统计项"""
    schedule_date: date
    doctor_id: str
    doctor_name: str
    morning_slots: int = 0
    afternoon_slots: int = 0
    evening_slots: int = 0
    morning_booked: int = 0
    afternoon_booked: int = 0
    evening_booked: int = 0


class ScheduleStatisticsResponse(BaseModel):
    """排班统计响应"""
    store_id: str
    store_name: str
    year: int
    month: int
    items: List[ScheduleStatisticsItem]


@router.get("/statistics", response_model=ScheduleStatisticsResponse, summary="获取排班统计")
async def get_schedule_statistics(
    store_id: Optional[str] = Query(None, description="门店ID"),
    year: int = Query(..., ge=2020, le=2100, description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取排班统计（按门店、月份）"""
    # 门店过滤
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter
    elif not store_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择门店")
    
    # 检查门店访问权限
    if not check_store_access(current_admin, store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权访问此门店数据")
    
    # 获取门店信息
    store_result = await db.execute(select(Store).where(Store.id == store_id))
    store = store_result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="门店不存在，请检查后重试")
    
    # 计算月份的开始和结束日期
    start_date = date(year, month, 1)
    _, last_day = monthrange(year, month)
    end_date = date(year, month, last_day)
    
    # 获取门店下所有医生
    doctors_result = await db.execute(
        select(Doctor).where(Doctor.store_id == store_id, Doctor.status == 1)
    )
    doctors = doctors_result.scalars().all()
    doctor_map = {d.id: d.name for d in doctors}
    
    # 汇总统计数据
    stats_dict = {}  # key: (date, doctor_id)
    
    # 1. 获取普通排班统计（添加 store_id 过滤，确保门店隔离）
    normal_result = await db.execute(
        select(Schedule)
        .where(
            and_(
                Schedule.store_id == store_id,
                Schedule.doctor_id.in_(list(doctor_map.keys())),
                Schedule.schedule_date >= start_date,
                Schedule.schedule_date <= end_date
            )
        )
    )
    normal_schedules = normal_result.scalars().all()
    
    for s in normal_schedules:
        key = (s.schedule_date, s.doctor_id)
        if key not in stats_dict:
            stats_dict[key] = {
                "morning_slots": 0,
                "afternoon_slots": 0,
                "evening_slots": 0,
                "morning_booked": 0,
                "afternoon_booked": 0,
                "evening_booked": 0
            }

        if s.time_slot == "morning":
            stats_dict[key]["morning_slots"] += s.total_slots
            stats_dict[key]["morning_booked"] += s.booked_slots
        elif s.time_slot == "afternoon":
            stats_dict[key]["afternoon_slots"] += s.total_slots
            stats_dict[key]["afternoon_booked"] += s.booked_slots
        elif s.time_slot == "evening":
            stats_dict[key]["evening_slots"] += s.total_slots
            stats_dict[key]["evening_booked"] += s.booked_slots
    
    # 2. 获取自定义排班统计（template_id为NULL的排班，添加 doctor_id 过滤确保门店隔离）
    custom_result = await db.execute(
        select(Schedule)
        .where(
            and_(
                Schedule.store_id == store_id,
                Schedule.doctor_id.in_(list(doctor_map.keys())),  # 只查询该门店下的医生
                Schedule.schedule_date >= start_date,
                Schedule.schedule_date <= end_date,
                Schedule.status == 1,
                Schedule.template_id.is_(None)  # 自定义排班
            )
        )
    )
    custom_schedule_list = custom_result.scalars().all()
    
    for s in custom_schedule_list:
        key = (s.schedule_date, s.doctor_id)
        if key not in stats_dict:
            stats_dict[key] = {
                "morning_slots": 0,
                "afternoon_slots": 0,
                "evening_slots": 0,
                "morning_booked": 0,
                "afternoon_booked": 0,
                "evening_booked": 0
            }

        # 根据时间判断上午/下午/晚间
        if s.start_time and s.start_time.hour < 12:
            stats_dict[key]["morning_slots"] += s.total_slots
            stats_dict[key]["morning_booked"] += s.booked_slots
        elif s.start_time and s.start_time.hour >= 18:
            stats_dict[key]["evening_slots"] += s.total_slots
            stats_dict[key]["evening_booked"] += s.booked_slots
        elif s.start_time:
            stats_dict[key]["afternoon_slots"] += s.total_slots
            stats_dict[key]["afternoon_booked"] += s.booked_slots
    
    # 构建结果
    items = []
    for (schedule_date, doctor_id), stats in sorted(stats_dict.items()):
        items.append(ScheduleStatisticsItem(
            schedule_date=schedule_date,
            doctor_id=doctor_id,
            doctor_name=doctor_map.get(doctor_id, ""),
            morning_slots=stats["morning_slots"],
            afternoon_slots=stats["afternoon_slots"],
            evening_slots=stats["evening_slots"],
            morning_booked=stats["morning_booked"],
            afternoon_booked=stats["afternoon_booked"],
            evening_booked=stats["evening_booked"]
        ))
    
    return ScheduleStatisticsResponse(
        store_id=store_id,
        store_name=store.name,
        year=year,
        month=month,
        items=items
    )


@router.get("/available/{doctor_id}", response_model=List[AvailableScheduleResponse], summary="获取可预约排班")
async def get_available_schedules(
    doctor_id: str,
    days: int = Query(14, ge=1, le=30),
    db: AsyncSession = Depends(get_db)
):
    """获取可预约排班（增强版：包含规则引擎信息）"""
    service = ScheduleService(db)
    rule_engine = RuleEngineService(db)
    schedules = await service.get_available(doctor_id, days=days)

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
            is_rest_day=is_rest_day_flag
        ))

    return result

@router.get("/{schedule_id}", response_model=ScheduleResponse, summary="获取排班详情")
async def get_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
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
        created_at=schedule.created_at,
        is_rest_day=is_rest_day
    )

@router.post("", response_model=ScheduleResponse, summary="创建排班")
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
        created_at=schedule.created_at,
        is_rest_day=is_rest_day
    )

@router.post("/batch", response_model=BatchOperateResponse, summary="批量创建排班")
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

@router.put("/{schedule_id}", response_model=ScheduleResponse, summary="更新排班")
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
        created_at=schedule.created_at,
        is_rest_day=is_rest_day
    )

class BatchScheduleRequest(BaseModel):
    """批量操作排班请求"""
    schedule_ids: List[str] = Field(..., min_length=1, description="排班ID列表")
    reason: Optional[str] = Field(None, max_length=200, description="操作原因")


@router.post("/batch-suspend", response_model=BatchOperateResponse, summary="批量停诊")
async def batch_suspend_schedules(
    data: BatchScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:update"))
):
    """批量停诊排班"""
    service = ScheduleService(db)

    try:
        affected_count = await service.batch_suspend(
            data.schedule_ids,
            data.reason,
            operator_id=current_admin.get("id")
        )
        return BatchOperateResponse(
            success=True,
            affected_count=affected_count,
            message=f"成功停诊 {affected_count} 条排班记录"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/batch-resume", response_model=BatchOperateResponse, summary="批量恢复排班")
async def batch_resume_schedules(
    data: BatchScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:update"))
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


@router.post("/batch-delete", response_model=BatchOperateResponse, summary="批量删除排班")
async def batch_delete_schedules(
    data: BatchScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:delete"))
):
    """批量删除排班（只能删除没有任何预约记录的排班）"""
    service = ScheduleService(db)
    
    try:
        affected_count = await service.batch_delete(data.schedule_ids)
        skipped = len(data.schedule_ids) - affected_count
        message = f"成功删除 {affected_count} 条排班记录"
        if skipped > 0:
            message += f"，{skipped} 条因存在预约记录而跳过"
        return BatchOperateResponse(
            success=True,
            affected_count=affected_count,
            message=message
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
