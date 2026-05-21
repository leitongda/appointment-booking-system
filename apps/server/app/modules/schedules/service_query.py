"""Read-oriented schedule queries."""

import json
import logging
import time
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import selectinload

from app.middleware.tenant_context import get_current_tenant_id
from app.models.doctor import Doctor
from app.models.doctor_booking_setting import DoctorBookingSetting
from app.models.rest_day import RestDay
from app.models.schedule import Schedule
from app.models.schedule_status import ScheduleStatus

logger = logging.getLogger(__name__)


def _invalidate_rest_days_cache(tenant_id: Optional[str] = None) -> None:
    """清除指定租户的休息日缓存（写操作后调用）。保留接口兼容，当前无进程内缓存。"""
    pass


def _build_rest_day_index(rest_days: Sequence[RestDay]) -> Dict[Tuple, List]:
    """为休息日构建按 (store_id, date) 分桶的索引，加速 is_rest_day 查找。

    返回 dict[(store_id, date)] -> [RestDay, ...]。
    doctor_ids 为 None 的记录（门店全员休息）也放入对应桶中。
    """
    index: Dict[Tuple, List] = {}
    for rd in rest_days:
        # 一条休息日可能覆盖多天，按每天入桶
        d = rd.start_date
        while d <= rd.end_date:
            key = (rd.store_id, d)
            index.setdefault(key, []).append(rd)
            d += timedelta(days=1)
    return index


class ScheduleQueryMixin:
    async def get_by_id(self, schedule_id: str) -> Optional[Schedule]:
        tenant_id = get_current_tenant_id()
        query = (
            select(Schedule).options(
                selectinload(Schedule.doctor).selectinload(Doctor.department)
            ).where(Schedule.id == schedule_id)
        )
        if tenant_id:
            query = query.where(Schedule.tenant_id == tenant_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_list(
        self,
        doctor_id: Optional[str] = None,
        store_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[int] = None,
        schedule_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[List[Schedule], int]:
        tenant_id = get_current_tenant_id()
        query = select(Schedule).options(
            selectinload(Schedule.doctor).selectinload(Doctor.department)
        )
        count_query = select(func.count(Schedule.id))

        if tenant_id:
            query = query.where(Schedule.tenant_id == tenant_id)
            count_query = count_query.where(Schedule.tenant_id == tenant_id)

        if doctor_id:
            query = query.where(Schedule.doctor_id == doctor_id)
            count_query = count_query.where(Schedule.doctor_id == doctor_id)
        if store_id:
            query = query.where(Schedule.store_id == store_id)
            count_query = count_query.where(Schedule.store_id == store_id)
        if start_date:
            query = query.where(Schedule.schedule_date >= start_date)
            count_query = count_query.where(Schedule.schedule_date >= start_date)
        if end_date:
            query = query.where(Schedule.schedule_date <= end_date)
            count_query = count_query.where(Schedule.schedule_date <= end_date)
        if status is not None:
            query = query.where(Schedule.status == status)
            count_query = count_query.where(Schedule.status == status)
        if schedule_status:
            query = query.where(Schedule.schedule_status == schedule_status)
            count_query = count_query.where(Schedule.schedule_status == schedule_status)

        query = (
            query.order_by(Schedule.schedule_date, Schedule.time_slot)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        schedules = list(result.scalars().all())
        total_count = count_result.scalar() or 0

        # 计算生效状态
        if schedules:
            await self._compute_effective_status(schedules)

        return schedules, total_count

    async def _compute_effective_status(self, schedules: List[Schedule]) -> None:
        """为排班列表计算生效状态（直接修改 Schedule 对象的附加属性）。"""
        if not schedules:
            return

        _t0 = time.monotonic()

        # 收集日期范围和医生ID
        min_date = min(s.schedule_date for s in schedules)
        max_date = max(s.schedule_date for s in schedules)
        doctor_ids = {s.doctor_id for s in schedules}

        # 批量加载休息日（带进程内 TTL 缓存）
        tenant_id = get_current_tenant_id()
        all_rest_days = await self._get_rest_days_cached(tenant_id, min_date, max_date)

        # 为休息日构建 (store_id, date) 索引，避免 O(N*M) 线性扫描
        rest_day_index = _build_rest_day_index(all_rest_days)

        # 批量加载该日期范围内的自定义排班（用于判断"被覆盖"，加租户过滤）
        custom_conditions = [
            Schedule.template_id.is_(None),
            Schedule.status == 1,
            Schedule.schedule_date >= min_date,
            Schedule.schedule_date <= max_date,
            Schedule.doctor_id.in_(list(doctor_ids)),
        ]
        if tenant_id:
            custom_conditions.append(Schedule.tenant_id == tenant_id)
        custom_result = await self.db.execute(
            select(Schedule).where(and_(*custom_conditions))
        )
        custom_schedules = list(custom_result.scalars().all())
        # 构建覆盖查找键: (doctor_id, date, start_time, end_time)
        custom_keys = {
            (s.doctor_id, s.schedule_date, s.start_time, s.end_time)
            for s in custom_schedules
            if s.start_time and s.end_time
        }
        custom_slot_keys = {
            (s.doctor_id, s.schedule_date, s.time_slot)
            for s in custom_schedules
        }

        for schedule in schedules:
            # 1. 停诊 (legacy status=0 或 schedule_status=suspended)
            if schedule.status == 0 or schedule.schedule_status == ScheduleStatus.SUSPENDED:
                schedule.effective_status = "suspended"
                continue

            # 1.5 已撤回
            if schedule.schedule_status == ScheduleStatus.WITHDRAWN:
                schedule.effective_status = "withdrawn"
                continue

            # 1.6 草稿
            if schedule.schedule_status == ScheduleStatus.DRAFT:
                schedule.effective_status = "draft"
                continue

            # 1.7 已结束
            if schedule.schedule_status == ScheduleStatus.FINISHED:
                schedule.effective_status = "finished"
                continue

            # 2. 自定义排班（最高优先级）
            if schedule.template_id is None:
                schedule.effective_status = "custom"
                continue

            # 3. 休息日检查（仅模板排班，使用索引加速）
            is_rest = self._is_rest_day_indexed(
                rest_day_index, schedule.schedule_date, schedule.store_id, schedule.doctor_id
            )
            if is_rest:
                schedule.effective_status = "rest_day"
                continue

            # 4. 被自定义排班覆盖检查
            if schedule.start_time and schedule.end_time:
                if (schedule.doctor_id, schedule.schedule_date, schedule.start_time, schedule.end_time) in custom_keys:
                    schedule.effective_status = "overridden"
                    continue
            elif schedule.time_slot:
                if (schedule.doctor_id, schedule.schedule_date, schedule.time_slot) in custom_slot_keys:
                    schedule.effective_status = "overridden"
                    continue

            # 5. 正常生效
            schedule.effective_status = "active"

        elapsed = time.monotonic() - _t0
        if elapsed > 0.1:
            logger.warning(
                "_compute_effective_status 耗时 %.3fs (排班数=%d, 休息日=%d, 自定义=%d)",
                elapsed, len(schedules), len(all_rest_days), len(custom_schedules),
            )

    async def _get_rest_days_cached(
        self,
        tenant_id: Optional[str],
        min_date: date,
        max_date: date,
    ) -> List[RestDay]:
        """查询指定日期范围内的活跃休息日。"""
        conditions = [RestDay.status == 1]
        if tenant_id:
            conditions.append(RestDay.tenant_id == tenant_id)
        result = await self.db.execute(select(RestDay).where(and_(*conditions)))
        all_rest_days = list(result.scalars().all())

        return [
            rd for rd in all_rest_days
            if rd.start_date <= max_date and rd.end_date >= min_date
        ]

    @staticmethod
    def _is_rest_day_indexed(
        rest_day_index: Dict[Tuple, List],
        check_date: date,
        store_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
    ) -> bool:
        """使用预构建索引判断休息日（O(1) 查找替代线性扫描）。"""
        if not store_id:
            return False
        bucket = rest_day_index.get((store_id, check_date))
        if not bucket:
            return False
        for rd in bucket:
            # 无 doctor_ids 表示门店所有医生休息
            if rd.doctor_ids is None:
                return True
            if doctor_id:
                try:
                    doctor_ids_list = json.loads(rd.doctor_ids)
                    if doctor_id in doctor_ids_list:
                        return True
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"解析休息日医生列表失败: rest_day_id={rd.id}")
        return False

    async def _get_booking_setting(
        self, doctor_id: str, store_id: Optional[str]
    ) -> Optional[DoctorBookingSetting]:
        stmt = (
            select(DoctorBookingSetting)
            .where(
                and_(
                    DoctorBookingSetting.doctor_id == doctor_id,
                    DoctorBookingSetting.status == 1,
                )
            )
        )
        if store_id:
            stmt = stmt.where(DoctorBookingSetting.store_id == store_id)
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(DoctorBookingSetting.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def _compute_booking_date_range(
        self, setting: DoctorBookingSetting
    ) -> Tuple[date, date]:
        today = date.today()
        start_date = today + timedelta(days=setting.booking_start_offset)
        end_date = start_date + timedelta(days=setting.booking_range_days)

        if setting.release_time and setting.release_time != "00:00":
            import pytz
            local_tz = pytz.timezone("Asia/Shanghai")
            now = datetime.now(local_tz)
            hour, minute = map(int, setting.release_time.split(":"))
            release_today = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if now < release_today:
                start_date = today + timedelta(days=setting.booking_start_offset + 1)
                end_date = start_date + timedelta(days=setting.booking_range_days)

        return start_date, end_date

    async def get_available(
        self,
        doctor_id: str,
        days: int = 14,
        store_id: Optional[str] = None,
    ) -> Tuple[List[Schedule], bool]:
        tenant_id = get_current_tenant_id()
        today = date.today()
        booking_setting_applied = False

        setting = await self._get_booking_setting(doctor_id, store_id)
        if setting:
            start_date, end_date = self._compute_booking_date_range(setting)
            booking_setting_applied = True
        else:
            start_date = today
            end_date = today + timedelta(days=days)

        # 号源拆分：患者端可预约判断使用 online_quota
        # 如果 online_quota 为 0（旧数据），回退到 total_slots
        from sqlalchemy import case
        effective_online_quota = case(
            (Schedule.online_quota > 0, Schedule.online_quota),
            else_=Schedule.total_slots,
        )

        conditions = [
            Schedule.doctor_id == doctor_id,
            Schedule.schedule_date >= start_date,
            Schedule.schedule_date <= end_date,
            Schedule.status == 1,
            Schedule.booked_slots < effective_online_quota,
            Schedule.schedule_status.in_(list(ScheduleStatus.BOOKABLE)),
        ]
        if tenant_id:
            conditions.append(Schedule.tenant_id == tenant_id)

        result = await self.db.execute(
            select(Schedule)
            .where(and_(*conditions))
            .order_by(Schedule.schedule_date, Schedule.time_slot)
        )
        schedules = list(result.scalars().all())

        # 使用带缓存的休息日查询 + 索引加速
        all_rest_days = await self._get_rest_days_cached(tenant_id, start_date, end_date)
        rest_day_index = _build_rest_day_index(all_rest_days)

        filtered_schedules = []
        for schedule in schedules:
            if schedule.template_id is None:
                filtered_schedules.append(schedule)
                continue

            is_rest = self._is_rest_day_indexed(
                rest_day_index, schedule.schedule_date, schedule.store_id, doctor_id
            )
            if not is_rest:
                filtered_schedules.append(schedule)

        schedule_map = {}
        for schedule in filtered_schedules:
            key = (schedule.schedule_date, schedule.start_time, schedule.end_time)
            if key not in schedule_map or schedule.template_id is None:
                schedule_map[key] = schedule

        return (
            sorted(schedule_map.values(), key=lambda s: (s.schedule_date, s.start_time or s.time_slot)),
            booking_setting_applied,
        )

    @staticmethod
    def _is_rest_day_cached(rest_days, check_date: date, store_id: Optional[str] = None, doctor_id: Optional[str] = None) -> bool:
        """使用预加载的休息日列表判断指定日期是否为休息日（内存操作，无 DB 查询）。"""
        from app.utils.schedule_utils import is_rest_day
        return is_rest_day(rest_days, check_date, store_id, doctor_id)
