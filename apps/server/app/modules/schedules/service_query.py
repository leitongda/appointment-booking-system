"""Read-oriented schedule queries."""

import json
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.middleware.tenant_context import get_current_tenant_id
from app.models.doctor import Doctor
from app.models.doctor_booking_setting import DoctorBookingSetting
from app.models.rest_day import RestDay
from app.models.schedule import Schedule
from app.models.store import Store


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

        # 收集日期范围和医生ID
        min_date = min(s.schedule_date for s in schedules)
        max_date = max(s.schedule_date for s in schedules)
        doctor_ids = {s.doctor_id for s in schedules}
        store_ids = {s.store_id for s in schedules if s.store_id}

        # 批量加载休息日（加租户过滤）
        tenant_id = get_current_tenant_id()
        rest_day_conditions = [
            RestDay.status == 1,
            RestDay.start_date <= max_date,
            RestDay.end_date >= min_date,
        ]
        if tenant_id:
            rest_day_conditions.append(RestDay.tenant_id == tenant_id)
        rest_days_result = await self.db.execute(
            select(RestDay).where(and_(*rest_day_conditions))
        )
        all_rest_days = list(rest_days_result.scalars().all())

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
            # 1. 停诊
            if schedule.status == 0:
                schedule.effective_status = "suspended"
                continue

            # 2. 自定义排班（最高优先级）
            if schedule.template_id is None:
                schedule.effective_status = "custom"
                continue

            # 3. 休息日检查（仅模板排班）
            is_rest = self._is_rest_day_cached(
                all_rest_days, schedule.schedule_date, schedule.store_id, schedule.doctor_id
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

    async def _get_booking_setting(
        self, doctor_id: str, store_id: Optional[str]
    ) -> Optional[DoctorBookingSetting]:
        stmt = (
            select(DoctorBookingSetting)
            .join(Store, DoctorBookingSetting.store_id == Store.id)
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
            stmt = stmt.where(Store.tenant_id == tenant_id)
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

        conditions = [
            Schedule.doctor_id == doctor_id,
            Schedule.schedule_date >= start_date,
            Schedule.schedule_date <= end_date,
            Schedule.status == 1,
            Schedule.booked_slots < Schedule.total_slots,
        ]
        if tenant_id:
            conditions.append(Schedule.tenant_id == tenant_id)

        result = await self.db.execute(
            select(Schedule)
            .where(and_(*conditions))
            .order_by(Schedule.schedule_date, Schedule.time_slot)
        )
        schedules = list(result.scalars().all())

        rest_days_query = select(RestDay).where(
            and_(
                RestDay.status == 1,
                RestDay.start_date <= end_date,
                RestDay.end_date >= start_date,
            )
        )
        rest_days_result = await self.db.execute(rest_days_query)
        all_rest_days = rest_days_result.scalars().all()

        filtered_schedules = []
        for schedule in schedules:
            if schedule.template_id is None:
                filtered_schedules.append(schedule)
                continue

            is_rest = self._is_rest_day_cached(all_rest_days, schedule.schedule_date, schedule.store_id, doctor_id)
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
