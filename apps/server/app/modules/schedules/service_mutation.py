"""Mutation-oriented schedule operations."""

import logging
import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.schemas.schedule import ScheduleBatchCreate, ScheduleCreate, ScheduleUpdate
from app.services.message_service import MessageService
from app.utils.audit import set_create_audit, set_update_audit
from app.utils.schedule_utils import get_time_slot_from_time

logger = logging.getLogger(__name__)


class ScheduleMutationMixin:
    async def create(self, data: ScheduleCreate, operator_id: Optional[str] = None) -> Schedule:
        time_slot = data.time_slot
        if not time_slot and data.start_time:
            time_slot = get_time_slot_from_time(data.start_time)
        elif not time_slot:
            raise ValueError("必须提供 time_slot 或 start_time")

        conditions = [
            Schedule.doctor_id == data.doctor_id,
            Schedule.schedule_date == data.schedule_date,
        ]
        if data.start_time and data.end_time:
            conditions.append(Schedule.start_time == data.start_time)
            conditions.append(Schedule.end_time == data.end_time)
        else:
            conditions.append(Schedule.time_slot == time_slot)

        existing = await self.db.execute(select(Schedule).where(and_(*conditions)))
        existing_schedule = existing.scalar_one_or_none()

        if existing_schedule:
            is_new_custom = data.template_id is None
            is_existing_normal = existing_schedule.template_id is not None
            is_existing_suspended = existing_schedule.status == 0

            if is_existing_suspended:
                raise ValueError("该时段已停诊，无法创建排班")

            if is_new_custom and is_existing_normal:
                if existing_schedule.booked_slots > 0:
                    raise ValueError("该时段普通排班已有预约，无法覆盖")
                await self.db.delete(existing_schedule)
                await self.db.flush()
            else:
                raise ValueError("该时段排班已存在")

        store_id = data.store_id
        if not store_id:
            doctor_result = await self.db.execute(select(Doctor).where(Doctor.id == data.doctor_id))
            doctor = doctor_result.scalar_one_or_none()
            if doctor:
                store_id = doctor.store_id

        schedule = Schedule(
            id=str(uuid.uuid4()),
            doctor_id=data.doctor_id,
            store_id=store_id,
            template_id=data.template_id,
            schedule_date=data.schedule_date,
            time_slot=time_slot,
            start_time=data.start_time,
            end_time=data.end_time,
            total_slots=data.total_slots,
            booked_slots=0,
            appointment_type=data.appointment_type or "normal",
            status=data.status,
        )
        set_create_audit(schedule, operator_id)
        self.db.add(schedule)
        await self.db.commit()
        await self.db.refresh(schedule)

        if data.template_id is None:
            await self._send_schedule_notification_to_doctor(
                doctor_id=data.doctor_id,
                title="新增排班通知",
                content=f"您有新增排班：{data.schedule_date.strftime('%Y年%m月%d日')}，请及时查看。",
                schedule_id=schedule.id,
            )

        return schedule

    async def batch_create(self, data: ScheduleBatchCreate, operator_id: Optional[str] = None) -> int:
        doctor_result = await self.db.execute(select(Doctor).where(Doctor.id == data.doctor_id))
        doctor = doctor_result.scalar_one_or_none()
        if not doctor:
            raise ValueError("医生不存在")

        store_id = doctor.store_id
        created_count = 0
        current_date = data.start_date

        while current_date <= data.end_date:
            weekday = current_date.isoweekday()
            if weekday in data.weekdays:
                for time_slot in data.time_slots:
                    existing = await self.db.execute(
                        select(Schedule).where(
                            and_(
                                Schedule.doctor_id == data.doctor_id,
                                Schedule.schedule_date == current_date,
                                Schedule.time_slot == time_slot,
                            )
                        )
                    )
                    if not existing.scalar_one_or_none():
                        schedule = Schedule(
                            id=str(uuid.uuid4()),
                            doctor_id=data.doctor_id,
                            store_id=store_id,
                            schedule_date=current_date,
                            time_slot=time_slot,
                            total_slots=data.total_slots,
                            booked_slots=0,
                            appointment_type="normal",
                            status=1,
                        )
                        set_create_audit(schedule, operator_id)
                        self.db.add(schedule)
                        created_count += 1
            current_date = current_date.fromordinal(current_date.toordinal() + 1)

        await self.db.commit()

        if created_count > 0:
            await self._send_schedule_notification_to_doctor(
                doctor_id=data.doctor_id,
                title="批量排班通知",
                content=(
                    f"您有 {created_count} 个新排班已创建"
                    f"（{data.start_date.strftime('%Y年%m月%d日')} 至 {data.end_date.strftime('%Y年%m月%d日')}），请及时查看。"
                ),
                schedule_id=None,
            )

        return created_count

    async def update(
        self, schedule_id: str, data: ScheduleUpdate, operator_id: Optional[str] = None
    ) -> Optional[Schedule]:
        schedule = await self.get_by_id(schedule_id)
        if not schedule:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "total_slots" in update_data and update_data["total_slots"] < schedule.booked_slots:
            raise ValueError("总号源数不能小于已预约数")

        for field, value in update_data.items():
            setattr(schedule, field, value)

        set_update_audit(schedule, operator_id)
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule

    async def batch_suspend(self, schedule_ids: List[str], reason: Optional[str] = None) -> int:
        if not schedule_ids:
            return 0

        result = await self.db.execute(
            select(Schedule)
            .options(selectinload(Schedule.doctor))
            .where(and_(Schedule.id.in_(schedule_ids), Schedule.status == 1))
        )
        schedules = result.scalars().all()

        affected_count = 0
        for schedule in schedules:
            schedule.status = 0
            affected_count += 1

        if affected_count > 0:
            await self.db.commit()
            await self._send_batch_suspend_notifications(schedules, reason)

        return affected_count

    async def _send_batch_suspend_notifications(
        self, schedules: List[Schedule], reason: Optional[str] = None
    ):
        try:
            schedule_ids = [s.id for s in schedules]
            if not schedule_ids:
                return

            message_service = MessageService(self.db)
            doctor_schedules = {}
            for schedule in schedules:
                doctor_schedules.setdefault(schedule.doctor_id, []).append(schedule)

            for doctor_id, doc_schedules in doctor_schedules.items():
                try:
                    dates = sorted(set(s.schedule_date for s in doc_schedules))
                    date_str = (
                        dates[0].strftime("%Y年%m月%d日")
                        if len(dates) == 1
                        else f"{dates[0].strftime('%Y年%m月%d日')} 至 {dates[-1].strftime('%Y年%m月%d日')}"
                    )
                    reason_text = f"（原因：{reason}）" if reason else ""
                    await message_service.send_schedule_notification(
                        doctor_id=doctor_id,
                        title="排班停诊通知",
                        content=f"您的 {len(doc_schedules)} 个排班已被停诊（{date_str}）{reason_text}。如有疑问请联系管理员。",
                        schedule_id=doc_schedules[0].id if len(doc_schedules) == 1 else None,
                    )
                except Exception as e:
                    logger.warning(f"医生停诊通知发送失败 (doctor_id={doctor_id}): {e}")

            appointments_result = await self.db.execute(
                select(Appointment)
                .options(selectinload(Appointment.schedule))
                .where(and_(Appointment.schedule_id.in_(schedule_ids), Appointment.status.in_([1, 2])))
            )
            appointments = appointments_result.scalars().all()
            if not appointments:
                return

            schedule_map = {s.id: s for s in schedules}
            for appointment in appointments:
                try:
                    schedule = schedule_map.get(appointment.schedule_id)
                    if not schedule:
                        continue

                    doctor_name = schedule.doctor.name if schedule.doctor else appointment.doctor_name or "医生"
                    schedule_date_str = schedule.schedule_date.strftime("%Y年%m月%d日")
                    time_slot_display = {
                        "AM": "上午",
                        "PM": "下午",
                        "morning": "上午",
                        "afternoon": "下午",
                        "evening": "晚间",
                        "NIGHT": "夜间",
                    }.get(schedule.time_slot, schedule.time_slot or "")
                    reason_text = f"原因：{reason}" if reason else "请重新预约其他时间"

                    await message_service.send_stop_clinic_notification(
                        user_id=appointment.user_id,
                        user_type="patient",
                        title="停诊通知",
                        content=f"您预约的{doctor_name}医生（{schedule_date_str} {time_slot_display}）因故停诊。{reason_text}，给您带来不便敬请谅解。",
                        appointment_id=appointment.id,
                    )
                except Exception as e:
                    logger.warning(f"停诊通知发送失败 (appointment_id={appointment.id}): {e}")
        except Exception as e:
            logger.warning(f"批量停诊通知发送失败: {e}")

    async def batch_resume(self, schedule_ids: List[str]) -> int:
        if not schedule_ids:
            return 0

        result = await self.db.execute(
            select(Schedule).where(and_(Schedule.id.in_(schedule_ids), Schedule.status == 0))
        )
        schedules = result.scalars().all()

        affected_count = 0
        for schedule in schedules:
            schedule.status = 1
            affected_count += 1

        if affected_count > 0:
            await self.db.commit()
        return affected_count

    async def delete(self, schedule_id: str) -> bool:
        schedule = await self.get_by_id(schedule_id)
        if not schedule:
            raise ValueError("排班不存在")

        appointments_result = await self.db.execute(
            select(Appointment.id).where(Appointment.schedule_id == schedule_id).limit(1)
        )
        if appointments_result.scalar_one_or_none():
            raise ValueError("该排班已有预约记录，无法删除")

        await self.db.delete(schedule)
        await self.db.commit()
        return True

    async def batch_delete(self, schedule_ids: List[str]) -> int:
        if not schedule_ids:
            return 0

        appointments_result = await self.db.execute(
            select(Appointment.schedule_id).where(Appointment.schedule_id.in_(schedule_ids)).distinct()
        )
        schedule_ids_with_appointments = {row[0] for row in appointments_result.fetchall()}
        deletable_schedule_ids = [sid for sid in schedule_ids if sid not in schedule_ids_with_appointments]
        if not deletable_schedule_ids:
            return 0

        result = await self.db.execute(select(Schedule).where(Schedule.id.in_(deletable_schedule_ids)))
        schedules = result.scalars().all()

        affected_count = 0
        for schedule in schedules:
            await self.db.delete(schedule)
            affected_count += 1

        if affected_count > 0:
            await self.db.commit()
        return affected_count
