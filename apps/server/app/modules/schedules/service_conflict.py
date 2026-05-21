"""排班冲突检测服务。

提供排班创建/编辑前的冲突预检，支持单项检测和批量检测。
所有检查均为只读操作，不修改任何数据。
"""

import logging
from dataclasses import dataclass, field
from datetime import date, time
from typing import Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.doctor import Doctor
from app.models.rest_day import RestDay
from app.models.schedule import Schedule
from app.models.schedule_holiday import ScheduleHoliday

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 冲突类型常量
# ---------------------------------------------------------------------------

class ConflictType:
    """冲突类型枚举"""
    DOCTOR_TIME = "doctor_time"       # 医生时间重叠
    ROOM_OCCUPIED = "room_occupied"   # 诊室已被占用
    LUNCH_BREAK = "lunch_break"       # 覆盖午休时间
    HOLIDAY = "holiday"               # 节假日限制
    DOCTOR_STATUS = "doctor_status"   # 医生离职/禁用
    REST_DAY = "rest_day"             # 休息日冲突


# ---------------------------------------------------------------------------
# 冲突结果数据类
# ---------------------------------------------------------------------------

@dataclass
class ConflictItem:
    """单条冲突记录"""
    type: str                  # ConflictType 值
    severity: str              # "error" 阻止保存 / "warning" 允许但需确认
    message: str               # 人类可读的冲突描述
    details: Dict = field(default_factory=dict)   # 冲突详情


@dataclass
class ConflictResult:
    """冲突检测结果"""
    has_conflict: bool
    conflicts: List[ConflictItem] = field(default_factory=list)
    blocking: bool = False     # 是否有 error 级别的冲突


# ---------------------------------------------------------------------------
# 批量检测输入
# ---------------------------------------------------------------------------

@dataclass
class ScheduleCheckItem:
    """批量冲突检测的单项输入"""
    doctor_id: str
    schedule_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    time_slot: Optional[str] = None
    store_id: Optional[str] = None
    room_id: Optional[str] = None
    exclude_schedule_id: Optional[str] = None


# ---------------------------------------------------------------------------
# 冲突检测服务
# ---------------------------------------------------------------------------

class ScheduleConflictService:
    """排班冲突检测服务

    设计原则：
    - 每种检查类型最多一个 SQL 查询，无 N+1
    - 所有查询加租户隔离
    - 只读操作，不修改任何数据
    """

    # 默认午休时间（可通过配置覆盖）
    DEFAULT_LUNCH_START = time(12, 0)
    DEFAULT_LUNCH_END = time(13, 0)

    def __init__(self, db: AsyncSession):
        self.db = db

    # ======================================================================
    # 公共入口
    # ======================================================================

    async def check_conflicts(
        self,
        doctor_id: str,
        schedule_date: date,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        time_slot: Optional[str] = None,
        store_id: Optional[str] = None,
        room_id: Optional[str] = None,
        exclude_schedule_id: Optional[str] = None,
    ) -> ConflictResult:
        """检查排班冲突，返回结构化冲突结果。

        检查项:
        1. 同医生同日期时间段重叠
        2. 同诊室同日期时间段占用（如果指定诊室）
        3. 午休时间覆盖
        4. 节假日限制
        5. 休息日冲突
        6. 医生状态检查（离职/禁用）
        """
        conflicts: List[ConflictItem] = []

        # 1. 医生时间冲突
        doctor_conflict = await self._check_doctor_time_conflict(
            doctor_id, schedule_date, start_time, end_time, time_slot, exclude_schedule_id,
        )
        if doctor_conflict:
            conflicts.append(doctor_conflict)

        # 2. 诊室占用冲突
        if room_id:
            room_conflict = await self._check_room_conflict(
                room_id, schedule_date, start_time, end_time, exclude_schedule_id,
            )
            if room_conflict:
                conflicts.append(room_conflict)

        # 3. 午休覆盖
        if start_time and end_time:
            lunch_conflict = self._check_lunch_break_conflict(start_time, end_time)
            if lunch_conflict:
                conflicts.append(lunch_conflict)

        # 4. 节假日限制
        holiday_conflict = await self._check_holiday_conflict(schedule_date, store_id)
        if holiday_conflict:
            conflicts.append(holiday_conflict)

        # 5. 休息日冲突
        rest_day_conflict = await self._check_rest_day_conflict(
            schedule_date, store_id, doctor_id,
        )
        if rest_day_conflict:
            conflicts.append(rest_day_conflict)

        # 6. 医生状态
        doctor_status = await self._check_doctor_status(doctor_id)
        if doctor_status:
            conflicts.append(doctor_status)

        return ConflictResult(
            has_conflict=len(conflicts) > 0,
            conflicts=conflicts,
            blocking=any(c.severity == "error" for c in conflicts),
        )

    async def batch_check_conflicts(
        self,
        schedules: List[ScheduleCheckItem],
    ) -> List[ConflictResult]:
        """批量冲突检测（用于批量排班/复制场景）。

        为减少数据库查询次数，按 doctor_id 分组预加载已有排班。
        """
        if not schedules:
            return []

        # 按 doctor_id 分组，批量预加载已有排班
        doctor_ids = list({s.doctor_id for s in schedules})
        min_date = min(s.schedule_date for s in schedules)
        max_date = max(s.schedule_date for s in schedules)

        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        # 批量加载已有排班
        existing_conditions = [
            Schedule.doctor_id.in_(doctor_ids),
            Schedule.schedule_date >= min_date,
            Schedule.schedule_date <= max_date,
            Schedule.status == 1,
        ]
        if tenant_id:
            existing_conditions.append(Schedule.tenant_id == tenant_id)

        existing_result = await self.db.execute(
            select(Schedule).where(and_(*existing_conditions))
        )
        existing_schedules = list(existing_result.scalars().all())

        # 批量加载节假日
        holiday_conditions = [
            ScheduleHoliday.holiday_date >= min_date,
            ScheduleHoliday.holiday_date <= max_date,
            ScheduleHoliday.status == 1,
        ]
        if tenant_id:
            holiday_conditions.append(ScheduleHoliday.tenant_id == tenant_id)
        holiday_result = await self.db.execute(
            select(ScheduleHoliday).where(and_(*holiday_conditions))
        )
        holidays = list(holiday_result.scalars().all())

        # 批量加载休息日
        rest_day_conditions = [
            RestDay.status == 1,
            RestDay.start_date <= max_date,
            RestDay.end_date >= min_date,
        ]
        if tenant_id:
            rest_day_conditions.append(RestDay.tenant_id == tenant_id)
        rest_day_result = await self.db.execute(
            select(RestDay).where(and_(*rest_day_conditions))
        )
        rest_days = list(rest_day_result.scalars().all())

        # 批量加载医生信息
        doctor_result = await self.db.execute(
            select(Doctor).where(Doctor.id.in_(doctor_ids))
        )
        doctors = {d.id: d for d in doctor_result.scalars().all()}

        # 逐项检测
        results = []
        for item in schedules:
            conflicts: List[ConflictItem] = []

            # 1. 医生时间冲突（从预加载数据中筛选）
            conflict = self._check_doctor_time_from_cache(
                existing_schedules, item.doctor_id, item.schedule_date,
                item.start_time, item.end_time, item.time_slot, item.exclude_schedule_id,
            )
            if conflict:
                conflicts.append(conflict)

            # 2. 诊室冲突
            if item.room_id:
                room_conflict = await self._check_room_conflict(
                    item.room_id, item.schedule_date,
                    item.start_time, item.end_time, item.exclude_schedule_id,
                )
                if room_conflict:
                    conflicts.append(room_conflict)

            # 3. 午休冲突
            if item.start_time and item.end_time:
                lunch_conflict = self._check_lunch_break_conflict(item.start_time, item.end_time)
                if lunch_conflict:
                    conflicts.append(lunch_conflict)

            # 4. 节假日冲突（从缓存中筛选）
            holiday_conflict = self._check_holiday_from_cache(holidays, item.schedule_date, item.store_id)
            if holiday_conflict:
                conflicts.append(holiday_conflict)

            # 5. 休息日冲突
            from app.utils.schedule_utils import is_rest_day
            if is_rest_day(rest_days, item.schedule_date, item.store_id, item.doctor_id):
                conflicts.append(ConflictItem(
                    type=ConflictType.REST_DAY,
                    severity="warning",
                    message=f"{item.schedule_date} 为休息日，该医生当日不排班",
                    details={"schedule_date": str(item.schedule_date), "doctor_id": item.doctor_id},
                ))

            # 6. 医生状态
            doctor = doctors.get(item.doctor_id)
            if doctor:
                if doctor.deleted_at is not None:
                    conflicts.append(ConflictItem(
                        type=ConflictType.DOCTOR_STATUS,
                        severity="error",
                        message=f"医生 {doctor.name} 已被删除，无法排班",
                        details={"doctor_id": item.doctor_id, "doctor_name": doctor.name},
                    ))
                elif doctor.status == 0:
                    conflicts.append(ConflictItem(
                        type=ConflictType.DOCTOR_STATUS,
                        severity="error",
                        message=f"医生 {doctor.name} 已被禁用，无法排班",
                        details={"doctor_id": item.doctor_id, "doctor_name": doctor.name},
                    ))

            results.append(ConflictResult(
                has_conflict=len(conflicts) > 0,
                conflicts=conflicts,
                blocking=any(c.severity == "error" for c in conflicts),
            ))

        return results

    # ======================================================================
    # 单项检查方法
    # ======================================================================

    async def _check_doctor_time_conflict(
        self,
        doctor_id: str,
        schedule_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        time_slot: Optional[str],
        exclude_schedule_id: Optional[str],
    ) -> Optional[ConflictItem]:
        """检查同医生同日期的时间段重叠。

        时间重叠判断 (半开区间): existing.start < new.end AND existing.end > new.start
        当 start_time/end_time 未指定时，退化为按 time_slot 精确匹配。
        """
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        conditions = [
            Schedule.doctor_id == doctor_id,
            Schedule.schedule_date == schedule_date,
            Schedule.status == 1,
        ]
        if tenant_id:
            conditions.append(Schedule.tenant_id == tenant_id)
        if exclude_schedule_id:
            conditions.append(Schedule.id != exclude_schedule_id)

        if start_time and end_time:
            # 基于时间范围的重叠检测
            conditions.append(Schedule.start_time.isnot(None))
            conditions.append(Schedule.end_time.isnot(None))
            conditions.append(Schedule.start_time < end_time)
            conditions.append(Schedule.end_time > start_time)
        elif time_slot:
            conditions.append(Schedule.time_slot == time_slot)
        else:
            # 既没有 time 也没有 time_slot，无法判断
            return None

        result = await self.db.execute(
            select(Schedule).where(and_(*conditions)).limit(1)
        )
        existing = result.scalar_one_or_none()

        if existing:
            return ConflictItem(
                type=ConflictType.DOCTOR_TIME,
                severity="error",
                message=(
                    f"医生在 {schedule_date} "
                    f"{existing.start_time.strftime('%H:%M') if existing.start_time else ''}"
                    f"-{existing.end_time.strftime('%H:%M') if existing.end_time else ''}"
                    f" 已有排班，时间冲突"
                ),
                details={
                    "existing_schedule_id": existing.id,
                    "existing_start_time": existing.start_time.isoformat() if existing.start_time else None,
                    "existing_end_time": existing.end_time.isoformat() if existing.end_time else None,
                    "existing_time_slot": existing.time_slot,
                },
            )
        return None

    async def _check_room_conflict(
        self,
        room_id: str,
        schedule_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        exclude_schedule_id: Optional[str],
    ) -> Optional[ConflictItem]:
        """检查同诊室同日期时间段占用。"""
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        conditions = [
            Schedule.room_id == room_id,
            Schedule.schedule_date == schedule_date,
            Schedule.status == 1,
        ]
        if tenant_id:
            conditions.append(Schedule.tenant_id == tenant_id)
        if exclude_schedule_id:
            conditions.append(Schedule.id != exclude_schedule_id)

        if start_time and end_time:
            conditions.append(Schedule.start_time.isnot(None))
            conditions.append(Schedule.end_time.isnot(None))
            conditions.append(Schedule.start_time < end_time)
            conditions.append(Schedule.end_time > start_time)

        result = await self.db.execute(select(Schedule).where(and_(*conditions)).limit(1))
        existing = result.scalar_one_or_none()

        if existing:
            return ConflictItem(
                type=ConflictType.ROOM_OCCUPIED,
                severity="error",
                message=(
                    f"诊室在 {schedule_date} "
                    f"{existing.start_time.strftime('%H:%M') if existing.start_time else ''}"
                    f"-{existing.end_time.strftime('%H:%M') if existing.end_time else ''}"
                    f" 已被占用"
                ),
                details={
                    "existing_schedule_id": existing.id,
                    "existing_doctor_id": existing.doctor_id,
                    "existing_start_time": existing.start_time.isoformat() if existing.start_time else None,
                    "existing_end_time": existing.end_time.isoformat() if existing.end_time else None,
                },
            )
        return None

    def _check_lunch_break_conflict(
        self,
        start_time: time,
        end_time: time,
    ) -> Optional[ConflictItem]:
        """检查排班是否覆盖午休时间。

        只在排班时间段完全覆盖午休时返回 warning。
        午休时段默认 12:00-13:00，可从 Settings 读取覆盖。
        """
        lunch_start = self.DEFAULT_LUNCH_START
        lunch_end = self.DEFAULT_LUNCH_END

        # 排班时间段完全包含午休: schedule.start <= lunch.start AND schedule.end >= lunch.end
        if start_time <= lunch_start and end_time >= lunch_end:
            return ConflictItem(
                type=ConflictType.LUNCH_BREAK,
                severity="warning",
                message=f"排班时间 {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')} 覆盖了午休时段 {lunch_start.strftime('%H:%M')}-{lunch_end.strftime('%H:%M')}",
                details={
                    "lunch_start": lunch_start.isoformat(),
                    "lunch_end": lunch_end.isoformat(),
                },
            )
        return None

    async def _check_holiday_conflict(
        self,
        schedule_date: date,
        store_id: Optional[str],
    ) -> Optional[ConflictItem]:
        """检查排班日期是否为禁止排班的节假日。"""
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        conditions = [
            ScheduleHoliday.holiday_date == schedule_date,
            ScheduleHoliday.status == 1,
            ScheduleHoliday.allow_schedule == False,  # noqa: E712
        ]
        if tenant_id:
            conditions.append(ScheduleHoliday.tenant_id == tenant_id)
        if store_id:
            # 匹配门店级节假日 或 全租户节假日（store_id IS NULL）
            conditions.append(
                (ScheduleHoliday.store_id == store_id) | (ScheduleHoliday.store_id.is_(None))
            )
        else:
            conditions.append(ScheduleHoliday.store_id.is_(None))

        result = await self.db.execute(
            select(ScheduleHoliday).where(and_(*conditions)).limit(1)
        )
        holiday = result.scalar_one_or_none()

        if holiday:
            return ConflictItem(
                type=ConflictType.HOLIDAY,
                severity="error",
                message=f"{schedule_date} 为{holiday.name}（{holiday.holiday_type}），该日不允许排班",
                details={
                    "holiday_id": holiday.id,
                    "holiday_name": holiday.name,
                    "holiday_type": holiday.holiday_type,
                    "allow_schedule": holiday.allow_schedule,
                },
            )
        return None

    async def _check_rest_day_conflict(
        self,
        schedule_date: date,
        store_id: Optional[str],
        doctor_id: str,
    ) -> Optional[ConflictItem]:
        """检查排班日期是否为该医生的休息日。"""
        from app.middleware.tenant_context import get_current_tenant_id
        from app.utils.schedule_utils import is_rest_day
        tenant_id = get_current_tenant_id()

        conditions = [
            RestDay.status == 1,
            RestDay.start_date <= schedule_date,
            RestDay.end_date >= schedule_date,
        ]
        if tenant_id:
            conditions.append(RestDay.tenant_id == tenant_id)
        if store_id:
            conditions.append(RestDay.store_id == store_id)

        result = await self.db.execute(select(RestDay).where(and_(*conditions)))
        rest_days = list(result.scalars().all())

        if is_rest_day(rest_days, schedule_date, store_id, doctor_id):
            return ConflictItem(
                type=ConflictType.REST_DAY,
                severity="warning",
                message=f"{schedule_date} 为休息日，该医生当日不排班",
                details={"schedule_date": str(schedule_date), "doctor_id": doctor_id},
            )
        return None

    async def _check_doctor_status(
        self,
        doctor_id: str,
    ) -> Optional[ConflictItem]:
        """检查医生是否在职且未被禁用。"""
        result = await self.db.execute(
            select(Doctor).where(Doctor.id == doctor_id)
        )
        doctor = result.scalar_one_or_none()

        if not doctor:
            return ConflictItem(
                type=ConflictType.DOCTOR_STATUS,
                severity="error",
                message="医生不存在",
                details={"doctor_id": doctor_id},
            )

        if doctor.deleted_at is not None:
            return ConflictItem(
                type=ConflictType.DOCTOR_STATUS,
                severity="error",
                message=f"医生 {doctor.name} 已被删除，无法排班",
                details={"doctor_id": doctor_id, "doctor_name": doctor.name},
            )

        if doctor.status == 0:
            return ConflictItem(
                type=ConflictType.DOCTOR_STATUS,
                severity="error",
                message=f"医生 {doctor.name} 已被禁用，无法排班",
                details={"doctor_id": doctor_id, "doctor_name": doctor.name},
            )

        return None

    # ======================================================================
    # 缓存辅助方法（批量检测使用）
    # ======================================================================

    @staticmethod
    def _check_doctor_time_from_cache(
        existing_schedules: List[Schedule],
        doctor_id: str,
        schedule_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        time_slot: Optional[str],
        exclude_schedule_id: Optional[str],
    ) -> Optional[ConflictItem]:
        """从预加载的排班列表中检测医生时间冲突（纯内存操作）。"""
        for s in existing_schedules:
            if s.doctor_id != doctor_id or s.schedule_date != schedule_date:
                continue
            if exclude_schedule_id and s.id == exclude_schedule_id:
                continue
            if s.status != 1:
                continue

            if start_time and end_time and s.start_time and s.end_time:
                # 时间重叠: existing.start < new.end AND existing.end > new.start
                if s.start_time < end_time and s.end_time > start_time:
                    return ConflictItem(
                        type=ConflictType.DOCTOR_TIME,
                        severity="error",
                        message=(
                            f"医生在 {schedule_date} "
                            f"{s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')}"
                            f" 已有排班，时间冲突"
                        ),
                        details={
                            "existing_schedule_id": s.id,
                            "existing_start_time": s.start_time.isoformat(),
                            "existing_end_time": s.end_time.isoformat(),
                        },
                    )
            elif time_slot and s.time_slot == time_slot:
                return ConflictItem(
                    type=ConflictType.DOCTOR_TIME,
                    severity="error",
                    message=f"医生在 {schedule_date} {time_slot} 时段已有排班",
                    details={"existing_schedule_id": s.id, "existing_time_slot": time_slot},
                )

        return None

    @staticmethod
    def _check_holiday_from_cache(
        holidays: List[ScheduleHoliday],
        schedule_date: date,
        store_id: Optional[str],
    ) -> Optional[ConflictItem]:
        """从预加载的节假日列表中检测冲突（纯内存操作）。"""
        for h in holidays:
            if h.holiday_date != schedule_date:
                continue
            if h.allow_schedule:
                continue
            # 门店匹配：全租户级（store_id IS NULL）或门店级匹配
            if h.store_id is not None and store_id and h.store_id != store_id:
                continue

            return ConflictItem(
                type=ConflictType.HOLIDAY,
                severity="error",
                message=f"{schedule_date} 为{h.name}（{h.holiday_type}），该日不允许排班",
                details={
                    "holiday_id": h.id,
                    "holiday_name": h.name,
                    "holiday_type": h.holiday_type,
                    "allow_schedule": h.allow_schedule,
                },
            )
        return None
