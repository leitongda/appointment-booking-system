import logging
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db

logger = logging.getLogger(__name__)
from app.api.deps import get_current_admin, require_permission
from app.core.config import settings
from app.core.redis import get_redis
from app.models.rest_day import RestDay
from app.models.schedule import Schedule
from app.modules.schedules.service import ScheduleService
from app.schemas.response import PageResponse
from app.schemas.schedule import (
    CustomScheduleCreate,
    CustomScheduleResponse,
    ScheduleCreate,
)
from app.utils.idempotency import check_idempotency, store_idempotency

router = APIRouter()


async def _check_single_schedule_rest_day(
    db: AsyncSession,
    schedule_date: date,
    store_id: str | None,
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
    store_id: str | None,
    doctor_id: str,
    rest_days: list
) -> bool:
    """检查指定排班是否在休息日（基于已查询的休息日列表）"""
    from app.utils.schedule_utils import is_rest_day
    return is_rest_day(rest_days, schedule_date, store_id, doctor_id)


@router.get(
    "/custom-schedules",
    response_model=PageResponse[CustomScheduleResponse],
    summary="获取自定义排班列表",
    description="""
    获取自定义排班列表（template_id为NULL的排班）。

    **支持筛选条件**：
    - store_id: 按门店筛选
    - department_id: 按科室筛选
    - doctor_id: 按医生筛选
    - start_date / end_date: 按排班日期范围筛选
    - appointment_type: 按预约类型筛选
    - status: 按状态筛选（1=正常 0=停诊）

    **数据隔离**：
    - 门店管理员只能查看本门店的排班
    """,
)
async def get_custom_schedules(
    store_id: str | None = None,
    department_id: str | None = None,
    doctor_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    appointment_type: str | None = None,
    status: int | None = Query(None, ge=0, le=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:read"))
):
    """获取自定义排班列表（template_id为NULL的排班）"""
    from app.models.doctor import Doctor

    query = select(Schedule).options(
        selectinload(Schedule.doctor).selectinload(Doctor.department),
        selectinload(Schedule.store)
    ).where(Schedule.template_id.is_(None))
    count_query = select(func.count(Schedule.id)).where(Schedule.template_id.is_(None))

    conditions = []
    if store_id:
        conditions.append(Schedule.store_id == store_id)
    if doctor_id:
        conditions.append(Schedule.doctor_id == doctor_id)
    if start_date:
        conditions.append(Schedule.schedule_date >= start_date)
    if end_date:
        conditions.append(Schedule.schedule_date <= end_date)
    if appointment_type:
        conditions.append(Schedule.appointment_type == appointment_type)
    if status is not None:
        conditions.append(Schedule.status == status)

    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))

    # 如果指定了department_id，需要通过doctor关联查询
    if department_id:
        query = query.join(Doctor).where(Doctor.department_id == department_id, Doctor.deleted_at.is_(None))
        count_query = count_query.join(Doctor).where(Doctor.department_id == department_id, Doctor.deleted_at.is_(None))

    query = query.order_by(Schedule.schedule_date, Schedule.start_time)
    query = query.offset((page - 1) * page_size).limit(page_size)

    result_query = await db.execute(query)
    schedules = result_query.scalars().all()

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # 查询日期范围内的所有有效休息日
    rest_days = []
    if schedules and (start_date or end_date):
        query_start = start_date or min(s.schedule_date for s in schedules)
        query_end = end_date or max(s.schedule_date for s in schedules)
        rest_day_conditions = [
            RestDay.status == 1,
            RestDay.start_date <= query_end,
            RestDay.end_date >= query_start
        ]
        if store_id:
            rest_day_conditions.append(RestDay.store_id == store_id)
        rest_day_result = await db.execute(
            select(RestDay).where(and_(*rest_day_conditions))
        )
        rest_days = rest_day_result.scalars().all()

    result = []
    for s in schedules:
        is_rest = _check_rest_day_for_schedule(
            s.schedule_date, s.store_id, s.doctor_id, rest_days
        )
        result.append(CustomScheduleResponse(
            id=s.id,
            store_id=s.store_id,
            store_name=s.store.name if s.store else None,
            department_id=s.doctor.department_id if s.doctor and s.doctor.department else None,
            department_name=s.doctor.department.name if s.doctor and s.doctor.department else None,
            doctor_id=s.doctor_id,
            doctor_name=s.doctor.name if s.doctor else None,
            schedule_date=s.schedule_date,
            start_time=s.start_time,
            end_time=s.end_time,
            appointment_type=s.appointment_type,
            max_patients=s.total_slots,
            booked_count=s.booked_slots,
            status=s.status,
            created_at=s.created_at,
            is_rest_day=is_rest
        ))

    return PageResponse(data=result, total=total, page=page, page_size=page_size)


@router.get(
    "/custom-schedules/effective",
    response_model=list[CustomScheduleResponse],
    summary="获取生效的自定义排班",
    description="""
    获取生效的自定义排班（template_id为NULL的排班）。

    **参数说明**：
    - store_id: 门店ID（可选）
    - doctor_id: 医生ID（可选）
    - start_date: 开始日期（必填）
    - end_date: 结束日期（必填）
    """,
)
async def get_effective_schedules(
    store_id: str | None = None,
    doctor_id: str | None = None,
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """获取生效的自定义排班（template_id为NULL的排班）"""
    from app.models.doctor import Doctor

    query = select(Schedule).options(
        selectinload(Schedule.doctor).selectinload(Doctor.department),
        selectinload(Schedule.store)
    ).where(
        and_(
            Schedule.template_id.is_(None),
            Schedule.status == 1,
            Schedule.schedule_date >= start_date,
            Schedule.schedule_date <= end_date
        )
    )

    if store_id:
        query = query.where(Schedule.store_id == store_id)
    if doctor_id:
        query = query.where(Schedule.doctor_id == doctor_id)

    query = query.order_by(Schedule.schedule_date, Schedule.start_time)

    result_query = await db.execute(query)
    schedules = result_query.scalars().all()

    # 查询日期范围内的所有有效休息日
    rest_days = []
    if schedules:
        rest_day_conditions = [
            RestDay.status == 1,
            RestDay.start_date <= end_date,
            RestDay.end_date >= start_date
        ]
        if store_id:
            rest_day_conditions.append(RestDay.store_id == store_id)
        rest_day_result = await db.execute(
            select(RestDay).where(and_(*rest_day_conditions))
        )
        rest_days = rest_day_result.scalars().all()

    result = []
    for s in schedules:
        is_rest = _check_rest_day_for_schedule(
            s.schedule_date, s.store_id, s.doctor_id, rest_days
        )
        result.append(CustomScheduleResponse(
            id=s.id,
            store_id=s.store_id,
            store_name=s.store.name if s.store else None,
            department_id=s.doctor.department_id if s.doctor and s.doctor.department else None,
            department_name=s.doctor.department.name if s.doctor and s.doctor.department else None,
            doctor_id=s.doctor_id,
            doctor_name=s.doctor.name if s.doctor else None,
            schedule_date=s.schedule_date,
            start_time=s.start_time,
            end_time=s.end_time,
            appointment_type=s.appointment_type,
            max_patients=s.total_slots,
            booked_count=s.booked_slots,
            status=s.status,
            created_at=s.created_at,
            is_rest_day=is_rest
        ))

    return result


@router.post(
    "/custom-schedules",
    response_model=list[CustomScheduleResponse],
    summary="创建自定义排班",
    description="""
    创建自定义排班（支持批量）。

    **权限要求**：管理员权限（schedule:create）。

    **业务规则**：
    - 支持批量创建多个日期的排班
    - 支持每个日期添加多个时段
    - 可选是否均分时段
    - 自定义排班没有模板ID（template_id为NULL）
    """,
)
async def create_custom_schedules(
    data: CustomScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:create")),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    """创建自定义排班（支持批量）"""
    from app.models.doctor import Doctor
    from app.utils.schedule_utils import get_time_slot_from_time, split_time_range

    tenant_id = current_admin.get("tenant_id", "")

    # 幂等性检查：如果提供了 Idempotency-Key，先查 Redis 缓存
    if idempotency_key:
        redis = await get_redis()
        cached = await check_idempotency(redis, idempotency_key, tenant_id)
        if cached is not None:
            return [CustomScheduleResponse(**item) for item in cached]

    service = ScheduleService(db)
    created_schedules = []

    try:
        for schedule_date in data.schedule_dates:
            for period in data.time_periods:
                # 判断是否需要均分时段
                if period.slot_count and period.slot_count > 1:
                    # 自动均分时段
                    time_slots = split_time_range(
                        period.start_time,
                        period.end_time,
                        period.slot_count
                    )
                    for slot_start, slot_end in time_slots:
                        time_slot = get_time_slot_from_time(slot_start)
                        schedule_data = ScheduleCreate(
                            doctor_id=data.doctor_id,
                            store_id=data.store_id,
                            schedule_date=schedule_date,
                            time_slot=time_slot,
                            start_time=slot_start,
                            end_time=slot_end,
                            total_slots=period.max_patients,
                            appointment_type=period.appointment_type.value,
                            status=1,
                            template_id=None  # 自定义排班没有模板ID
                        )
                        schedule = await service.create(schedule_data)
                        created_schedules.append(schedule)
                else:
                    # 不均分，直接使用指定的时间段
                    time_slot = get_time_slot_from_time(period.start_time)
                    schedule_data = ScheduleCreate(
                        doctor_id=data.doctor_id,
                        store_id=data.store_id,
                        schedule_date=schedule_date,
                        time_slot=time_slot,
                        start_time=period.start_time,
                        end_time=period.end_time,
                        total_slots=period.max_patients,
                        appointment_type=period.appointment_type.value,
                        status=1,
                        template_id=None  # 自定义排班没有模板ID
                    )
                    schedule = await service.create(schedule_data)
                    created_schedules.append(schedule)

        # 重新加载关联数据
        result = []

        # 查询日期范围内的休息日（用于计算 is_rest_day）
        rest_days = []
        if created_schedules:
            min_date = min(s.schedule_date for s in created_schedules)
            max_date = max(s.schedule_date for s in created_schedules)
            rest_day_result = await db.execute(
                select(RestDay).where(
                    and_(
                        RestDay.status == 1,
                        RestDay.start_date <= max_date,
                        RestDay.end_date >= min_date,
                        RestDay.store_id == data.store_id
                    )
                )
            )
            rest_days = rest_day_result.scalars().all()

        # Re-fetch all created schedules with relationships in one query (fix N+1)
        if created_schedules:
            ids = [s.id for s in created_schedules]
            eager_result = await db.execute(
                select(Schedule)
                .where(Schedule.id.in_(ids))
                .options(
                    selectinload(Schedule.doctor).selectinload(Doctor.department),
                    selectinload(Schedule.store),
                )
            )
            created_schedules = list(eager_result.scalars().all())

        for s in created_schedules:
            is_rest = _check_rest_day_for_schedule(
                s.schedule_date, s.store_id, s.doctor_id, rest_days
            )
            result.append(CustomScheduleResponse(
                id=s.id,
                store_id=s.store_id,
                store_name=s.store.name if s.store else None,
                department_id=s.doctor.department_id if s.doctor and s.doctor.department else None,
                department_name=s.doctor.department.name if s.doctor and s.doctor.department else None,
                doctor_id=s.doctor_id,
                doctor_name=s.doctor.name if s.doctor else None,
                schedule_date=s.schedule_date,
                start_time=s.start_time,
                end_time=s.end_time,
                appointment_type=s.appointment_type,
                max_patients=s.total_slots,
                booked_count=s.booked_slots,
                status=s.status,
                created_at=s.created_at,
                is_rest_day=is_rest
            ))

        # 幂等性存储：成功后缓存响应
        if idempotency_key:
            redis = await get_redis()
            await store_idempotency(
                redis, idempotency_key, tenant_id,
                [item.model_dump(mode="json") for item in result],
            )

        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/custom-schedules/{schedule_id}",
    summary="删除自定义排班",
    description="""
    删除自定义排班（仅能删除template_id为NULL的排班）。

    **权限要求**：管理员权限（schedule:delete）。

    **业务规则**：
    - 只能删除自定义排班（template_id为NULL）
    - 已有预约记录的排班无法删除
    """,
)
async def delete_custom_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:delete"))
):
    """删除自定义排班（仅能删除template_id为NULL的排班）"""
    service = ScheduleService(db)

    schedule = await service.get_by_id(schedule_id)
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="排班不存在")

    if schedule.template_id is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只能删除自定义排班")

    if schedule.booked_slots > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该排班已有预约，无法删除")

    await db.delete(schedule)
    await db.commit()

    return {"message": "删除成功"}
