import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants.appointment import (
    ACTIVE_APPOINTMENT_STATUSES,
    APPOINTMENT_QUERY_OPTIONS,
    APPOINTMENT_STATUS,
)
from app.core.events import dispatch_event_email
from app.middleware.tenant_context import get_current_tenant_id
from app.models.appointment import Appointment
from app.models.rest_day import RestDay
from app.models.rule_set import AppointmentCheckin  # noqa: F401
from app.models.schedule import Schedule
from app.schemas.appointment import AppointmentStatistics

logger = logging.getLogger(__name__)


class AppointmentServiceBase:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _resolve_tenant(self, tenant_id: str | None) -> str | None:
        """显式锚点优先；未传时回退请求上下文（兼容既有内部调用）"""
        return tenant_id if tenant_id is not None else get_current_tenant_id()

    def _apply_tenant_scope(self, query, model, tenant_id: str | None):
        """为查询追加租户范围（锚点为空时保持全平台视图）"""
        effective_tenant_id = self._resolve_tenant(tenant_id)
        if effective_tenant_id:
            query = query.where(model.tenant_id == effective_tenant_id)
        return query

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

    async def get_by_id(self, appointment_id: str, tenant_id: str | None = None) -> Appointment | None:
        query = select(Appointment).options(*APPOINTMENT_QUERY_OPTIONS).where(Appointment.id == appointment_id)
        query = self._apply_tenant_scope(query, Appointment, tenant_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_appointment_no(self, appointment_no: str, tenant_id: str | None = None) -> Appointment | None:
        query = (
            select(Appointment)
            .options(*APPOINTMENT_QUERY_OPTIONS)
            .where(Appointment.appointment_no == appointment_no)
        )
        query = self._apply_tenant_scope(query, Appointment, tenant_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_list(
        self,
        user_id: str | None = None,
        doctor_id: str | None = None,
        patient_id: str | None = None,
        store_id: str | None = None,
        status: int | None = None,
        assistant_confirm_status: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        keyword: str | None = None,
        department_id: str | None = None,
        created_start: datetime | None = None,
        created_end: datetime | None = None,
        page: int = 1,
        page_size: int = 10,
        tenant_id: str | None = None,
    ) -> tuple[list[Appointment], int]:
        effective_tenant_id = self._resolve_tenant(tenant_id)
        query = select(Appointment).options(*APPOINTMENT_QUERY_OPTIONS)
        count_query = select(func.count(Appointment.id))
        schedule_joined = False
        if effective_tenant_id:
            query = query.where(Appointment.tenant_id == effective_tenant_id)
            count_query = count_query.where(Appointment.tenant_id == effective_tenant_id)

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
        if assistant_confirm_status is not None:
            query = query.where(Appointment.assistant_confirm_status == assistant_confirm_status)
            count_query = count_query.where(Appointment.assistant_confirm_status == assistant_confirm_status)
        if keyword:
            keyword_filter = or_(
                Appointment.appointment_no.ilike(f"%{keyword}%"),
                Appointment.patient_name.ilike(f"%{keyword}%"),
                Appointment.patient_phone.ilike(f"%{keyword}%"),
            )
            query = query.where(keyword_filter)
            count_query = count_query.where(keyword_filter)
        if department_id:
            from app.models.doctor import Doctor

            query = query.join(Doctor, Appointment.doctor_id == Doctor.id)
            count_query = count_query.join(Doctor, Appointment.doctor_id == Doctor.id)
            query = query.where(Doctor.department_id == department_id)
            count_query = count_query.where(Doctor.department_id == department_id)
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

    async def get_today_by_doctor(self, doctor_id: str, tenant_id: str | None = None) -> list[Appointment]:
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
                            APPOINTMENT_STATUS["SEEING"],
                        ]
                    ),
                )
            )
        )
        query = self._apply_tenant_scope(query, Appointment, tenant_id)
        result = await self.db.execute(query.order_by(Appointment.queue_number))
        return list(result.scalars().all())

    async def get_statistics(
        self,
        doctor_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        store_id: str | list[str] | None = None,
        tenant_id: str | None = None,
    ) -> AppointmentStatistics:
        tenant_id = self._resolve_tenant(tenant_id)
        base_query = select(Appointment.status, func.count(Appointment.id))
        if tenant_id:
            base_query = base_query.where(Appointment.tenant_id == tenant_id)
        if doctor_id:
            base_query = base_query.where(Appointment.doctor_id == doctor_id)
        if start_date or end_date or store_id:
            base_query = base_query.join(Schedule, Schedule.id == Appointment.schedule_id)
        if start_date:
            base_query = base_query.where(Schedule.schedule_date >= start_date)
        if end_date:
            base_query = base_query.where(Schedule.schedule_date <= end_date)
        if store_id:
            if isinstance(store_id, list):
                base_query = base_query.where(Schedule.store_id.in_(store_id))
            else:
                base_query = base_query.where(Schedule.store_id == store_id)
        base_query = base_query.group_by(Appointment.status)
        result = await self.db.execute(base_query)
        status_counts = dict(result.all())
        return AppointmentStatistics(
            total=sum(status_counts.values()),
            confirmed=status_counts.get(1, 0),
            signed_in=status_counts.get(2, 0),
            in_progress=status_counts.get(4, 0),
            completed=status_counts.get(5, 0),
            cancelled=status_counts.get(6, 0),
            no_show=status_counts.get(8, 0),  # NO_SHOW(爽约)
        )

    async def get_queue_info(self, doctor_id: str, tenant_id: str | None = None) -> dict:
        today = date.today()
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
        in_progress_query = self._apply_tenant_scope(in_progress_query, Appointment, tenant_id)
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
        waiting_query = self._apply_tenant_scope(waiting_query, Appointment, tenant_id)
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
        passed_query = self._apply_tenant_scope(passed_query, Appointment, tenant_id)
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

    async def get_today_pending_by_user_and_store(
        self, user_id: str, store_id: str, tenant_id: str | None = None
    ) -> list[Appointment]:
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
        effective_tenant_id = self._resolve_tenant(tenant_id)
        return [
            a
            for a in result.scalars().all()
            if not effective_tenant_id or a.tenant_id == effective_tenant_id
        ]

    async def get_checkin_queue(
        self,
        store_id: str | None = None,
        doctor_id: str | None = None,
        target_date: date | None = None,
        tenant_id: str | None = None,
    ) -> list[Appointment]:
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
        query = self._apply_tenant_scope(query, Appointment, tenant_id)
        query = query.order_by(Appointment.sign_in_time)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def check_duplicate_same_day(
        self,
        user_id: str,
        patient_id: str,
        schedule_date: date,
        time_slot: str,
        tenant_id: str | None = None,
    ) -> list[Appointment]:
        query = (
            select(Appointment)
            .join(Schedule)
            .options(selectinload(Appointment.schedule))
            .where(
                and_(
                    Appointment.user_id == user_id,
                    Appointment.patient_id == patient_id,
                    Schedule.schedule_date == schedule_date,
                    Schedule.time_slot == time_slot,
                    Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
                )
            )
        )
        query = self._apply_tenant_scope(query, Appointment, tenant_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _count_user_store_daily_appointments(
        self,
        user_id: str,
        store_id: str | None,
        schedule_date: date,
        tenant_id: str | None = None,
    ) -> int:
        query = (
            select(func.count(Appointment.id))
            .join(Schedule)
            .where(
                and_(
                    Appointment.user_id == user_id,
                    Schedule.schedule_date == schedule_date,
                    Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
                )
            )
        )
        query = self._apply_tenant_scope(query, Appointment, tenant_id)
        if store_id:
            query = query.where(Schedule.store_id == store_id)
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def _count_user_doctor_active_appointments(
        self,
        user_id: str,
        doctor_id: str,
        tenant_id: str | None = None,
    ) -> int:
        query = select(func.count(Appointment.id)).where(
            and_(
                Appointment.user_id == user_id,
                Appointment.doctor_id == doctor_id,
                Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
            )
        )
        query = self._apply_tenant_scope(query, Appointment, tenant_id)
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def _check_rest_day(
        self,
        check_date: date,
        store_id: str | None = None,
        doctor_id: str | None = None,
        tenant_id: str | None = None,
    ) -> bool:
        try:
            query = select(RestDay).where(
                and_(RestDay.status == 1, RestDay.start_date <= check_date, RestDay.end_date >= check_date)
            )
            if store_id:
                query = query.where(RestDay.store_id == store_id)
            result = await self.db.execute(query)
            rest_days = result.scalars().all()
            effective_tenant_id = self._resolve_tenant(tenant_id)
            if effective_tenant_id:
                rest_days = [r for r in rest_days if r.tenant_id == effective_tenant_id]
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
