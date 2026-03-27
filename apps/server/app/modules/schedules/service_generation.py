"""Rest-day checks and template-based generation for schedules."""

import json
import logging
import uuid
from datetime import date, time, timedelta
from typing import Optional, Tuple

from sqlalchemy import and_, select

from app.models.doctor import Doctor
from app.models.rest_day import RestDay
from app.models.schedule import Schedule
from app.modules.messages.service_messages import MessageService
from app.utils.schedule_utils import get_time_slot_from_time

logger = logging.getLogger(__name__)


class ScheduleGenerationMixin:
    async def _check_rest_day(
        self, check_date: date, store_id: Optional[str] = None, doctor_id: Optional[str] = None
    ) -> bool:
        try:
            query = select(RestDay).where(
                and_(
                    RestDay.status == 1,
                    RestDay.start_date <= check_date,
                    RestDay.end_date >= check_date,
                )
            )
            if store_id:
                query = query.where(RestDay.store_id == store_id)

            result = await self.db.execute(query)
            rest_days = result.scalars().all()

            for rd in rest_days:
                if not doctor_id or rd.doctor_ids is None:
                    return True
                try:
                    doctor_ids_list = json.loads(rd.doctor_ids)
                    if doctor_id in doctor_ids_list:
                        return True
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"解析休息日医生列表失败: rest_day_id={rd.id}, error={e}")
            return False
        except Exception as e:
            logger.error(f"检查休息日失败: date={check_date}, store_id={store_id}, error={e}")
            return False

    async def _create_schedule_if_not_exists(
        self,
        doctor_id: str,
        store_id: Optional[str],
        schedule_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        time_slot: str,
        total_slots: int,
        appointment_type: str = "normal",
        template_id: Optional[str] = None,
        check_rest_day: bool = True,
        check_duplicate: bool = True,
    ) -> Tuple[Optional[Schedule], bool]:
        if check_rest_day and await self._check_rest_day(schedule_date, store_id, doctor_id):
            return None, False

        if check_duplicate:
            conditions = [Schedule.doctor_id == doctor_id, Schedule.schedule_date == schedule_date]
            if start_time and end_time:
                conditions.append(Schedule.start_time == start_time)
                conditions.append(Schedule.end_time == end_time)
            else:
                conditions.append(Schedule.time_slot == time_slot)

            existing = await self.db.execute(select(Schedule).where(and_(*conditions)))
            if existing.scalar_one_or_none():
                return None, False

        if not store_id:
            doctor_result = await self.db.execute(select(Doctor).where(Doctor.id == doctor_id))
            doctor = doctor_result.scalar_one_or_none()
            if doctor:
                store_id = doctor.store_id

        schedule = Schedule(
            id=str(uuid.uuid4()),
            doctor_id=doctor_id,
            store_id=store_id,
            template_id=template_id,
            schedule_date=schedule_date,
            time_slot=time_slot,
            start_time=start_time,
            end_time=end_time,
            total_slots=total_slots,
            appointment_type=appointment_type,
            booked_slots=0,
            status=1,
        )
        self.db.add(schedule)
        return schedule, True

    async def _generate_from_template_internal(
        self,
        template_id: str,
        start_date: date,
        end_date: date,
        check_rest_day: bool = True,
        auto_commit: bool = True,
    ) -> int:
        from app.models.schedule_template import ScheduleTemplate
        from app.utils.schedule_utils import should_generate_schedule, split_time_range_with_breaks

        template_result = await self.db.execute(
            select(ScheduleTemplate).where(ScheduleTemplate.id == template_id)
        )
        template = template_result.scalar_one_or_none()
        if not template or template.status != 1:
            return 0

        weekdays = template.weekday_list
        if not weekdays:
            return 0

        break_times = template.break_times_list or []
        time_slots = split_time_range_with_breaks(
            template.start_time, template.end_time, template.slot_count, break_times
        )

        created_count = 0
        current_date = start_date
        while current_date <= end_date:
            weekday = current_date.isoweekday()
            if weekday in weekdays and should_generate_schedule(current_date, template.schedule_mode):
                for slot_start, slot_end in time_slots:
                    time_slot = get_time_slot_from_time(slot_start)
                    schedule, created = await self._create_schedule_if_not_exists(
                        doctor_id=template.doctor_id,
                        store_id=template.store_id,
                        schedule_date=current_date,
                        start_time=slot_start,
                        end_time=slot_end,
                        time_slot=time_slot,
                        total_slots=template.slot_capacity,
                        appointment_type=template.appointment_type,
                        template_id=template.id,
                        check_rest_day=check_rest_day,
                        check_duplicate=True,
                    )
                    if created:
                        created_count += 1
            current_date += timedelta(days=1)

        if auto_commit:
            await self.db.commit()
        return created_count

    async def generate_from_template(
        self,
        template_id: str,
        start_date: date,
        end_date: date,
        check_rest_day: bool = True,
    ) -> int:
        return await self._generate_from_template_internal(
            template_id=template_id,
            start_date=start_date,
            end_date=end_date,
            check_rest_day=check_rest_day,
            auto_commit=True,
        )

    async def _send_schedule_notification_to_doctor(
        self, doctor_id: str, title: str, content: str, schedule_id: Optional[str] = None
    ):
        try:
            message_service = MessageService(self.db)
            await message_service.send_schedule_notification(
                doctor_id=doctor_id,
                title=title,
                content=content,
                schedule_id=schedule_id,
            )
        except Exception as e:
            logger.warning(f"排班通知发送失败 (doctor_id={doctor_id}): {e}")
