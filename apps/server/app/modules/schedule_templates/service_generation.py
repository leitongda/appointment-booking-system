"""Generation, batch operations, and copy helpers for schedule templates."""

import json
import uuid
from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, delete, func, select

from app.models.schedule import Schedule
from app.models.schedule_generation_log import ScheduleGenerationLog
from app.models.schedule_template import ScheduleTemplate
from app.schemas.schedule_generation_log import CheckGeneratedResponse
from app.schemas.schedule_template import ScheduleBatchAddRequest, ScheduleGenerateRequest
from app.utils.audit import set_create_audit
from app.utils.schedule_utils import (
    get_time_slot_from_time,
    should_generate_schedule,
    split_time_range_with_breaks,
)


class ScheduleTemplateGenerationMixin:
    async def generate_schedules(self, data: ScheduleGenerateRequest) -> int:
        from app.services.schedule_service import ScheduleService

        schedule_service = ScheduleService(self.db)
        created_count = 0
        now = datetime.now()

        for template_id in data.template_ids:
            count = await schedule_service._generate_from_template_internal(
                template_id=template_id,
                start_date=data.start_date,
                end_date=data.end_date,
                check_rest_day=True,
                auto_commit=False,
            )
            created_count += count
            if count > 0:
                template = await self.get_by_id(template_id)
                if template:
                    template.last_generated_at = now

        await self.db.commit()
        return created_count

    async def batch_add_schedules(self, data: ScheduleBatchAddRequest) -> int:
        now = datetime.now()
        break_times_json = None
        break_times_list = []
        if data.break_times:
            for bt in data.break_times:
                bt_dict = {
                    "startTime": bt.start_time.strftime("%H:%M")
                    if hasattr(bt.start_time, "strftime")
                    else str(bt.start_time),
                    "endTime": bt.end_time.strftime("%H:%M")
                    if hasattr(bt.end_time, "strftime")
                    else str(bt.end_time),
                }
                break_times_list.append(bt_dict)
            break_times_json = json.dumps(break_times_list)

        template = ScheduleTemplate(
            id=str(uuid.uuid4()),
            name=f"批量添加-{data.start_date}至{data.end_date}",
            store_id=data.store_id,
            doctor_id=data.doctor_id,
            department_id=data.department_id,
            weekdays=json.dumps(data.weekdays) if data.weekdays else "[]",
            appointment_type=data.appointment_type.value,
            start_time=data.start_time,
            end_time=data.end_time,
            slot_count=data.slot_count,
            slot_capacity=data.slot_capacity,
            schedule_mode=data.schedule_mode.value,
            break_times=break_times_json,
            status=1,
        )
        self.db.add(template)
        await self.db.flush()

        template_id = template.id
        created_count = 0
        time_slots = split_time_range_with_breaks(
            data.start_time, data.end_time, data.slot_count, break_times_list
        )

        current_date = data.start_date
        while current_date <= data.end_date:
            weekday = current_date.isoweekday()
            if weekday in data.weekdays and should_generate_schedule(current_date, data.schedule_mode.value):
                for slot_start, slot_end in time_slots:
                    time_slot = get_time_slot_from_time(slot_start)
                    existing = await self.db.execute(
                        select(Schedule).where(
                            and_(
                                Schedule.doctor_id == data.doctor_id,
                                Schedule.schedule_date == current_date,
                                Schedule.start_time == slot_start,
                                Schedule.end_time == slot_end,
                            )
                        )
                    )
                    if not existing.scalar_one_or_none():
                        schedule = Schedule(
                            id=str(uuid.uuid4()),
                            doctor_id=data.doctor_id,
                            store_id=data.store_id,
                            template_id=template_id,
                            schedule_date=current_date,
                            time_slot=time_slot,
                            start_time=slot_start,
                            end_time=slot_end,
                            total_slots=data.slot_capacity,
                            appointment_type=data.appointment_type.value,
                            booked_slots=0,
                            status=1,
                        )
                        self.db.add(schedule)
                        created_count += 1
            current_date += timedelta(days=1)

        if created_count > 0:
            template.last_generated_at = now

        await self.db.commit()
        return created_count

    async def check_generated(
        self,
        template_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> CheckGeneratedResponse:
        query = select(Schedule).where(Schedule.template_id == template_id)
        if start_date:
            query = query.where(Schedule.schedule_date >= start_date)
        if end_date:
            query = query.where(Schedule.schedule_date <= end_date)

        result = await self.db.execute(query)
        schedules = result.scalars().all()
        if not schedules:
            return CheckGeneratedResponse(has_generated=False, schedule_count=0, date_range_count=0)

        all_dates = [s.schedule_date for s in schedules]
        return CheckGeneratedResponse(
            has_generated=True,
            schedule_count=len(schedules),
            date_range_count=len(schedules),
            earliest_date=min(all_dates) if all_dates else None,
            latest_date=max(all_dates) if all_dates else None,
        )

    async def batch_delete_schedules(
        self,
        template_id: str,
        operator_id: Optional[str] = None,
        operator_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        future_only: bool = True,
    ) -> int:
        today = date.today()
        conditions = [Schedule.template_id == template_id]
        if future_only:
            conditions.append(Schedule.schedule_date >= today)
        if start_date:
            conditions.append(Schedule.schedule_date >= start_date)
        if end_date:
            conditions.append(Schedule.schedule_date <= end_date)
        conditions.append(Schedule.booked_slots == 0)

        count_query = select(func.count(Schedule.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        affected_count = count_result.scalar() or 0

        if affected_count > 0:
            await self.db.execute(delete(Schedule).where(and_(*conditions)))
            log = ScheduleGenerationLog(
                id=str(uuid.uuid4()),
                template_id=template_id,
                operator_id=operator_id,
                operator_name=operator_name,
                action_type="delete",
                start_date=start_date or (today if future_only else None),
                end_date=end_date,
                affected_count=affected_count,
                remark=f"批量删除排班，删除 {affected_count} 条记录",
            )
            self.db.add(log)
            await self.db.commit()

        return affected_count

    async def batch_suspend_schedules(
        self,
        template_id: str,
        operator_id: Optional[str] = None,
        operator_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        future_only: bool = True,
    ) -> int:
        today = date.today()
        conditions = [Schedule.template_id == template_id, Schedule.status == 1]
        if future_only:
            conditions.append(Schedule.schedule_date >= today)
        if start_date:
            conditions.append(Schedule.schedule_date >= start_date)
        if end_date:
            conditions.append(Schedule.schedule_date <= end_date)

        query = select(Schedule).where(and_(*conditions))
        result = await self.db.execute(query)
        schedules = result.scalars().all()

        affected_count = 0
        for schedule in schedules:
            schedule.status = 0
            affected_count += 1

        if affected_count > 0:
            log = ScheduleGenerationLog(
                id=str(uuid.uuid4()),
                template_id=template_id,
                operator_id=operator_id,
                operator_name=operator_name,
                action_type="suspend",
                start_date=start_date or (today if future_only else None),
                end_date=end_date,
                affected_count=affected_count,
                remark=f"批量停诊，停诊 {affected_count} 条记录",
            )
            self.db.add(log)
            await self.db.commit()

        return affected_count

    async def log_generation(
        self,
        template_id: str,
        action_type: str,
        affected_count: int,
        operator_id: Optional[str] = None,
        operator_name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        remark: Optional[str] = None,
    ) -> ScheduleGenerationLog:
        log = ScheduleGenerationLog(
            id=str(uuid.uuid4()),
            template_id=template_id,
            operator_id=operator_id,
            operator_name=operator_name,
            action_type=action_type,
            start_date=start_date,
            end_date=end_date,
            affected_count=affected_count,
            remark=remark,
        )
        self.db.add(log)
        await self.db.commit()
        return log

    async def generate_schedules_with_capacity(
        self,
        template_ids: List[str],
        start_date: date,
        end_date: date,
        capacity_overrides: dict = None,
    ) -> int:
        created_count = 0
        now = datetime.now()

        for template_id in template_ids:
            template = await self.get_by_id(template_id)
            if not template or template.status != 1:
                continue

            weekdays = template.weekday_list
            if not weekdays:
                continue

            break_times = template.break_times_list or []
            time_slots = split_time_range_with_breaks(
                template.start_time, template.end_time, template.slot_count, break_times
            )

            current_date = start_date
            while current_date <= end_date:
                weekday = current_date.isoweekday()
                if weekday in weekdays and should_generate_schedule(current_date, template.schedule_mode):
                    for slot_start, slot_end in time_slots:
                        existing = await self.db.execute(
                            select(Schedule).where(
                                and_(
                                    Schedule.doctor_id == template.doctor_id,
                                    Schedule.schedule_date == current_date,
                                    Schedule.start_time == slot_start,
                                    Schedule.end_time == slot_end,
                                )
                            )
                        )
                        if not existing.scalar_one_or_none():
                            time_slot = get_time_slot_from_time(slot_start)
                            capacity = template.slot_capacity
                            if capacity_overrides:
                                key = (
                                    current_date.isoformat(),
                                    slot_start.strftime("%H:%M"),
                                    slot_end.strftime("%H:%M"),
                                )
                                if key in capacity_overrides:
                                    capacity = capacity_overrides[key]

                            schedule = Schedule(
                                id=str(uuid.uuid4()),
                                doctor_id=template.doctor_id,
                                store_id=template.store_id,
                                template_id=template.id,
                                schedule_date=current_date,
                                time_slot=time_slot,
                                start_time=slot_start,
                                end_time=slot_end,
                                total_slots=capacity,
                                appointment_type=template.appointment_type,
                                booked_slots=0,
                                status=1,
                            )
                            self.db.add(schedule)
                            created_count += 1
                current_date += timedelta(days=1)

            if created_count > 0:
                template.last_generated_at = now

        await self.db.commit()
        return created_count

    async def copy_to_doctors(
        self,
        template_id: str,
        target_doctor_ids: List[str],
        overrides: dict = None,
    ) -> int:
        from app.models.doctor import Doctor

        template = await self.get_by_id(template_id)
        if not template:
            raise ValueError("原排班规则不存在")

        doctor_result = await self.db.execute(select(Doctor).where(Doctor.id.in_(target_doctor_ids)))
        doctors = {d.id: d for d in doctor_result.scalars().all()}
        if not doctors:
            raise ValueError("未找到有效的目标医生")

        overrides = overrides or {}
        created_count = 0

        for doctor_id in target_doctor_ids:
            doctor = doctors.get(doctor_id)
            if not doctor:
                continue

            base_name = overrides.get("name") or template.name
            new_name = f"{base_name}（{doctor.name}）"
            weekdays = overrides.get("weekdays") or template.weekday_list
            weekdays_json = json.dumps(weekdays) if isinstance(weekdays, list) else template.weekdays

            if "break_times" in overrides and overrides["break_times"] is not None:
                break_times_list = []
                for bt in overrides["break_times"]:
                    if hasattr(bt, "start_time"):
                        bt_dict = {
                            "startTime": bt.start_time.strftime("%H:%M")
                            if hasattr(bt.start_time, "strftime")
                            else str(bt.start_time),
                            "endTime": bt.end_time.strftime("%H:%M")
                            if hasattr(bt.end_time, "strftime")
                            else str(bt.end_time),
                        }
                    elif isinstance(bt, dict):
                        start_time = bt.get("start_time") or bt.get("startTime")
                        end_time = bt.get("end_time") or bt.get("endTime")
                        bt_dict = {
                            "startTime": start_time.strftime("%H:%M")
                            if hasattr(start_time, "strftime")
                            else str(start_time),
                            "endTime": end_time.strftime("%H:%M")
                            if hasattr(end_time, "strftime")
                            else str(end_time),
                        }
                    else:
                        bt_dict = bt
                    break_times_list.append(bt_dict)
                break_times_json = json.dumps(break_times_list)
            else:
                break_times_json = template.break_times

            start_time = overrides.get("start_time") or template.start_time
            end_time = overrides.get("end_time") or template.end_time
            if isinstance(start_time, str):
                try:
                    start_time = datetime.strptime(start_time, "%H:%M").time()
                except ValueError:
                    start_time = datetime.strptime(start_time, "%H:%M:%S").time()
            if isinstance(end_time, str):
                try:
                    end_time = datetime.strptime(end_time, "%H:%M").time()
                except ValueError:
                    end_time = datetime.strptime(end_time, "%H:%M:%S").time()

            new_template = ScheduleTemplate(
                id=str(uuid.uuid4()),
                name=new_name,
                store_id=template.store_id,
                doctor_id=doctor_id,
                department_id=doctor.department_id,
                weekdays=weekdays_json,
                appointment_type=overrides.get("appointment_type") or template.appointment_type,
                start_time=start_time,
                end_time=end_time,
                slot_count=overrides.get("slot_count")
                if overrides.get("slot_count") is not None
                else template.slot_count,
                slot_capacity=overrides.get("slot_capacity")
                if overrides.get("slot_capacity") is not None
                else template.slot_capacity,
                schedule_mode=overrides.get("schedule_mode") or template.schedule_mode,
                break_times=break_times_json,
                status=1,
            )
            set_create_audit(new_template, None)
            self.db.add(new_template)
            created_count += 1

        await self.db.commit()
        return created_count
