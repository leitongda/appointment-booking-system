"""Read-oriented schedule queries."""

import json
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.middleware.tenant_context import get_current_tenant_id
from app.models.doctor import Doctor
from app.models.rest_day import RestDay
from app.models.schedule import Schedule


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
        return list(result.scalars().all()), count_result.scalar() or 0

    async def get_available(self, doctor_id: str, days: int = 14) -> List[Schedule]:
        tenant_id = get_current_tenant_id()
        today = date.today()
        end_date = today + timedelta(days=days)

        conditions = [
            Schedule.doctor_id == doctor_id,
            Schedule.schedule_date >= today,
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

        # 批量查询休息日，避免 N+1 查询
        rest_days_query = select(RestDay).where(
            and_(
                RestDay.status == 1,
                RestDay.start_date <= end_date,
                RestDay.end_date >= today,
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

        return sorted(schedule_map.values(), key=lambda s: (s.schedule_date, s.start_time or s.time_slot))

    @staticmethod
    def _is_rest_day_cached(rest_days, check_date: date, store_id: Optional[str] = None, doctor_id: Optional[str] = None) -> bool:
        """使用预加载的休息日列表判断指定日期是否为休息日（内存操作，无 DB 查询）。"""
        for rd in rest_days:
            if rd.start_date > check_date or rd.end_date < check_date:
                continue
            if store_id and rd.store_id != store_id:
                continue
            if not doctor_id or rd.doctor_ids is None:
                return True
            try:
                doctor_ids_list = json.loads(rd.doctor_ids)
                if doctor_id in doctor_ids_list:
                    return True
            except (json.JSONDecodeError, TypeError):
                pass
        return False
