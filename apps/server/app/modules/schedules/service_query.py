"""Read-oriented schedule queries."""

from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.models.doctor import Doctor
from app.models.schedule import Schedule


class ScheduleQueryMixin:
    async def get_by_id(self, schedule_id: str) -> Optional[Schedule]:
        result = await self.db.execute(
            select(Schedule).options(
                selectinload(Schedule.doctor).selectinload(Doctor.department)
            ).where(Schedule.id == schedule_id)
        )
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
        query = select(Schedule).options(
            selectinload(Schedule.doctor).selectinload(Doctor.department)
        )
        count_query = select(func.count(Schedule.id))

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
        today = date.today()
        end_date = today + timedelta(days=days)

        result = await self.db.execute(
            select(Schedule)
            .where(
                and_(
                    Schedule.doctor_id == doctor_id,
                    Schedule.schedule_date >= today,
                    Schedule.schedule_date <= end_date,
                    Schedule.status == 1,
                    Schedule.booked_slots < Schedule.total_slots,
                )
            )
            .order_by(Schedule.schedule_date, Schedule.time_slot)
        )
        schedules = list(result.scalars().all())

        filtered_schedules = []
        for schedule in schedules:
            if schedule.template_id is None:
                filtered_schedules.append(schedule)
                continue

            is_rest_day = await self._check_rest_day(schedule.schedule_date, schedule.store_id, doctor_id)
            if not is_rest_day:
                filtered_schedules.append(schedule)

        schedule_map = {}
        for schedule in filtered_schedules:
            key = (schedule.schedule_date, schedule.start_time, schedule.end_time)
            if key not in schedule_map or schedule.template_id is None:
                schedule_map[key] = schedule

        return sorted(schedule_map.values(), key=lambda s: (s.schedule_date, s.start_time or s.time_slot))
