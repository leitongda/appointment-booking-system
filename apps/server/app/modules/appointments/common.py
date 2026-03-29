from datetime import date, datetime
import logging
from typing import List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.events import EventType, dispatch_event_email
from app.middleware.tenant_context import get_current_tenant_id
from app.models.appointment import Appointment
from app.models.rest_day import RestDay
from app.models.schedule import Schedule
from app.schemas.appointment import AppointmentStatistics

logger = logging.getLogger(__name__)

APPOINTMENT_STATUS = {
    "PENDING": 0,
    "CONFIRMED": 1,
    "SIGNED": 2,
    "WAITING": 3,
    "SEEING": 4,
    "COMPLETED": 5,
    "CANCELLED": 6,
    "EXPIRED": 7,
    "CLOSED": 8,
}


class AppointmentServiceBase:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _compat(self, name: str, default):
        from app.modules.appointments import service as compat_module

        return getattr(compat_module, name, default)

    def _dispatch_email_event(
        self,
        event_type: str,
        appointment: "Appointment",
        schedule: Optional["Schedule"] = None,
    ) -> None:
        try:
            sched = schedule or getattr(appointment, "schedule", None)
            if not sched:
                return

            time_slot_map = {
                "morning": "上午",
                "afternoon": "下午",
                "evening": "晚间",
            }
            context = {
                "patient_name": appointment.patient_name or "",
                "doctor_name": appointment.doctor_name or "",
                "department_name": appointment.department_name or "",
                "appointment_no": appointment.appointment_no or "",
                "appointment_date": sched.schedule_date.strftime("%Y年%m月%d日") if sched.schedule_date else "",
                "appointment_time": time_slot_map.get(sched.time_slot, sched.time_slot or ""),
            }
            dispatcher = self._compat("dispatch_event_email", dispatch_event_email)
            dispatcher(sched.store_id, event_type, context)
        except Exception as exc:
            logger.warning(f"邮件事件钩子分发失败: event={event_type}, error={exc}")

    async def get_by_id(self, appointment_id: str) -> Optional[Appointment]:
        query = select(Appointment).options(selectinload(Appointment.schedule)).where(Appointment.id == appointment_id)
        tenant_id = get_current_tenant_id()
        if tenant_id:
            query = query.where(Appointment.tenant_id == tenant_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_appointment_no(self, appointment_no: str) -> Optional[Appointment]:
        query = (
            select(Appointment)
            .options(selectinload(Appointment.schedule))
            .where(Appointment.appointment_no == appointment_no)
        )
        tenant_id = get_current_tenant_id()
        if tenant_id:
            query = query.where(Appointment.tenant_id == tenant_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_list(
        self,
        user_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        store_id: Optional[str] = None,
        status: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        keyword: Optional[str] = None,
        department_id: Optional[str] = None,
        created_start: Optional[datetime] = None,
        created_end: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[List[Appointment], int]:
        tenant_id = get_current_tenant_id()
        query = select(Appointment).options(selectinload(Appointment.schedule))
        count_query = select(func.count(Appointment.id))
        schedule_joined = False
        if tenant_id:
            query = query.where(Appointment.tenant_id == tenant_id)
            count_query = count_query.where(Appointment.tenant_id == tenant_id)

        if user_id:
            query = query.where(Appointment.user_id == user_id)
            count_query = count_query.where(Appointment.user_id == user_id)
        if doctor_id:
            query = query.where(Appointment.doctor_id == doctor_id)
            count_query = count_query.where(Appointment.doctor_id == doctor_id)
        if patient_id:
            query = query.where(Appointment.patient_id == patient_id)
            count_query = count_query.where(Appointment.patient_id == patient_id)
        if store_id:
            if not schedule_joined:
                query = query.join(Schedule)
                count_query = count_query.join(Schedule)
                schedule_joined = True
            query = query.where(Schedule.store_id == store_id)
            count_query = count_query.where(Schedule.store_id == store_id)
        if status is not None:
            query = query.where(Appointment.status == status)
            count_query = count_query.where(Appointment.status == status)
        if keyword:
            keyword_filter = or_(
                Appointment.appointment_no.ilike(f"%{keyword}%"),
                Appointment.patient_name.ilike(f"%{keyword}%"),
                Appointment.patient_phone.ilike(f"%{keyword}%"),
            )
            query = query.where(keyword_filter)
            count_query = count_query.where(keyword_filter)
        if department_id:
            from app.models.department import Department

            dept_result = await self.db.execute(select(Department.name).where(Department.id == department_id))
            dept_name = dept_result.scalar_one_or_none()
            if dept_name:
                query = query.where(Appointment.department_name == dept_name)
                count_query = count_query.where(Appointment.department_name == dept_name)
        if start_date or end_date:
            if not schedule_joined:
                query = query.join(Schedule)
                count_query = count_query.join(Schedule)
                schedule_joined = True
            if start_date:
                query = query.where(Schedule.schedule_date >= start_date)
                count_query = count_query.where(Schedule.schedule_date >= start_date)
            if end_date:
                query = query.where(Schedule.schedule_date <= end_date)
                count_query = count_query.where(Schedule.schedule_date <= end_date)
        if created_start:
            query = query.where(Appointment.created_at >= created_start)
            count_query = count_query.where(Appointment.created_at >= created_start)
        if created_end:
            query = query.where(Appointment.created_at <= created_end)
            count_query = count_query.where(Appointment.created_at <= created_end)

        query = query.order_by(Appointment.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        return list(result.scalars().all()), count_result.scalar() or 0

    async def get_today_by_doctor(self, doctor_id: str) -> List[Appointment]:
        today = date.today()
        query = (
            select(Appointment)
            .join(Schedule)
            .where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Schedule.schedule_date == today,
                    Appointment.status.in_(
                        [
                            APPOINTMENT_STATUS["CONFIRMED"],
                            APPOINTMENT_STATUS["SIGNED"],
                            APPOINTMENT_STATUS["WAITING"],
                            APPOINTMENT_STATUS["SEEING"],
                        ]
                    ),
                )
            )
        )
        tenant_id = get_current_tenant_id()
        if tenant_id:
            query = query.where(Appointment.tenant_id == tenant_id)
        result = await self.db.execute(query.order_by(Appointment.queue_number))
        return list(result.scalars().all())

    async def get_statistics(
        self,
        doctor_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> AppointmentStatistics:
        tenant_id = get_current_tenant_id()
        base_query = select(Appointment.status, func.count(Appointment.id))
        if tenant_id:
            base_query = base_query.where(Appointment.tenant_id == tenant_id)
        if doctor_id:
            base_query = base_query.where(Appointment.doctor_id == doctor_id)
        base_query = base_query.group_by(Appointment.status)
        result = await self.db.execute(base_query)
        status_counts = dict(result.all())
        return AppointmentStatistics(
            total=sum(status_counts.values()),
            pending=status_counts.get(1, 0),
            signed_in=status_counts.get(2, 0),
            in_progress=status_counts.get(3, 0),
            completed=status_counts.get(5, 0),
            cancelled=status_counts.get(6, 0),
            no_show=status_counts.get(7, 0),
        )

    async def get_queue_info(self, doctor_id: str) -> dict:
        today = date.today()
        tenant_id = get_current_tenant_id()
        in_progress_query = (
            select(Appointment)
            .join(Schedule)
            .options(selectinload(Appointment.patient))
            .where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Schedule.schedule_date == today,
                    Appointment.status == APPOINTMENT_STATUS["SEEING"],
                )
            )
        )
        if tenant_id:
            in_progress_query = in_progress_query.where(Appointment.tenant_id == tenant_id)
        in_progress_result = await self.db.execute(in_progress_query)
        current = in_progress_result.scalar_one_or_none()

        waiting_query = (
            select(Appointment)
            .join(Schedule)
            .options(selectinload(Appointment.patient))
            .where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Schedule.schedule_date == today,
                    Appointment.status == APPOINTMENT_STATUS["SIGNED"],
                )
            )
        )
        if tenant_id:
            waiting_query = waiting_query.where(Appointment.tenant_id == tenant_id)
        waiting_result = await self.db.execute(waiting_query.order_by(Appointment.sign_in_time))
        waiting_list = list(waiting_result.scalars().all())

        passed_query = (
            select(Appointment)
            .join(Schedule)
            .options(selectinload(Appointment.patient))
            .where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Schedule.schedule_date == today,
                    Appointment.status == APPOINTMENT_STATUS["EXPIRED"],
                )
            )
        )
        if tenant_id:
            passed_query = passed_query.where(Appointment.tenant_id == tenant_id)
        passed_result = await self.db.execute(passed_query.order_by(Appointment.queue_number))
        passed_list = list(passed_result.scalars().all())

        return {
            "current": {
                "id": current.id,
                "queueNumber": current.queue_number,
                "patientName": current.patient.name if current and current.patient else None,
                "callTime": current.call_time.isoformat() if current and current.call_time else None,
            }
            if current
            else None,
            "waitingCount": len(waiting_list),
            "waitingList": [
                {
                    "id": a.id,
                    "queueNumber": a.queue_number,
                    "patientName": a.patient.name if a.patient else None,
                    "signInTime": a.sign_in_time.isoformat() if a.sign_in_time else None,
                }
                for a in waiting_list[:10]
            ],
            "passedCount": len(passed_list),
            "passedList": [
                {
                    "id": a.id,
                    "queueNumber": a.queue_number,
                    "patientName": a.patient.name if a.patient else None,
                }
                for a in passed_list
            ],
        }

    async def get_today_pending_by_user_and_store(self, user_id: str, store_id: str) -> List[Appointment]:
        from app.models.doctor import Doctor

        today = date.today()
        result = await self.db.execute(
            select(Appointment)
            .join(Schedule)
            .options(
                selectinload(Appointment.schedule),
                selectinload(Appointment.patient),
                selectinload(Appointment.doctor).selectinload(Doctor.department),
            )
            .where(
                and_(
                    Appointment.user_id == user_id,
                    Schedule.store_id == store_id,
                    Schedule.schedule_date == today,
                    Appointment.status == APPOINTMENT_STATUS["CONFIRMED"],
                )
            )
            .order_by(Schedule.time_slot)
        )
        return list(result.scalars().all())

    async def get_checkin_queue(
        self,
        store_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
        target_date: Optional[date] = None,
    ) -> List[Appointment]:
        from app.models.doctor import Doctor

        target_date = target_date or date.today()
        query = (
            select(Appointment)
            .join(Schedule)
            .options(
                selectinload(Appointment.schedule),
                selectinload(Appointment.patient),
                selectinload(Appointment.doctor).selectinload(Doctor.department),
            )
            .where(
                and_(
                    Schedule.schedule_date == target_date,
                    Appointment.status.in_(
                        [
                            APPOINTMENT_STATUS["SIGNED"],
                            APPOINTMENT_STATUS["WAITING"],
                            APPOINTMENT_STATUS["SEEING"],
                            APPOINTMENT_STATUS["COMPLETED"],
                        ]
                    ),
                )
            )
        )
        if store_id:
            query = query.where(Schedule.store_id == store_id)
        if doctor_id:
            query = query.where(Appointment.doctor_id == doctor_id)
        query = query.order_by(Appointment.sign_in_time)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def check_duplicate_same_day(
        self,
        user_id: str,
        patient_id: str,
        schedule_date: date,
        time_slot: str,
    ) -> List[Appointment]:
        result = await self.db.execute(
            select(Appointment)
            .join(Schedule)
            .options(selectinload(Appointment.schedule))
            .where(
                and_(
                    Appointment.patient_id == patient_id,
                    Schedule.schedule_date == schedule_date,
                    Schedule.time_slot == time_slot,
                    Appointment.status.in_(
                        [
                            APPOINTMENT_STATUS["CONFIRMED"],
                            APPOINTMENT_STATUS["SIGNED"],
                            APPOINTMENT_STATUS["WAITING"],
                        ]
                    ),
                )
            )
        )
        return list(result.scalars().all())

    async def _count_user_store_daily_appointments(
        self,
        user_id: str,
        store_id: Optional[str],
        schedule_date: date,
    ) -> int:
        query = (
            select(func.count(Appointment.id))
            .join(Schedule)
            .where(
                and_(
                    Appointment.user_id == user_id,
                    Schedule.schedule_date == schedule_date,
                    Appointment.status.in_(
                        [
                            APPOINTMENT_STATUS["CONFIRMED"],
                            APPOINTMENT_STATUS["SIGNED"],
                            APPOINTMENT_STATUS["WAITING"],
                            APPOINTMENT_STATUS["SEEING"],
                        ]
                    ),
                )
            )
        )
        if store_id:
            query = query.where(Schedule.store_id == store_id)
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def _check_rest_day(
        self,
        check_date: date,
        store_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
    ) -> bool:
        try:
            query = select(RestDay).where(
                and_(RestDay.status == 1, RestDay.start_date <= check_date, RestDay.end_date >= check_date)
            )
            if store_id:
                query = query.where(RestDay.store_id == store_id)
            result = await self.db.execute(query)
            rest_days = result.scalars().all()
            for rest_day in rest_days:
                if not doctor_id or rest_day.doctor_ids is None:
                    return True
                try:
                    import json

                    doctor_ids_list = json.loads(rest_day.doctor_ids)
                    if doctor_id in doctor_ids_list:
                        return True
                except Exception:
                    pass
            return False
        except Exception:
            return False
