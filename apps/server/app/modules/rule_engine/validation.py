"""Conflict, capacity, and grace-period checks for the rule engine."""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pytz
from sqlalchemy import and_, func, select

from app.models.appointment import Appointment
from app.models.rule_set import RuleBookingPolicy, RuleCapacityPolicy, RuleCheckinPolicy
from app.models.schedule import Schedule
from app.models.waitlist import WaitlistEntry
from app.modules.rule_engine.monitoring import monitor_performance


class RuleEngineValidationMixin:
    @monitor_performance("check_booking_conflicts")
    async def check_booking_conflicts(
        self,
        db,
        shift_id: str,
        user_id: str,
        policy: RuleBookingPolicy,
        booking_time: datetime,
        schedule: Optional[Schedule] = None,
    ) -> Dict[str, Any]:
        if policy.per_user_per_shift and policy.per_user_per_shift > 0:
            existing_count = await db.execute(
                select(func.count(Appointment.id)).where(
                    and_(
                        Appointment.schedule_id == shift_id,
                        Appointment.user_id == user_id,
                        Appointment.status.in_([1, 2]),
                    )
                )
            )
            count = existing_count.scalar() or 0
            if count >= policy.per_user_per_shift:
                return {
                    "allowed": False,
                    "reason": f"每班次最多可预约{policy.per_user_per_shift}次，您已预约{count}次",
                    "conflict_with": None,
                }

        if policy.conflict_same_shift == "REJECT":
            existing = await db.execute(
                select(Appointment)
                .where(
                    and_(
                        Appointment.schedule_id == shift_id,
                        Appointment.user_id == user_id,
                        Appointment.status.in_([1, 2]),
                    )
                )
                .limit(1)
            )
            if existing.scalar_one_or_none():
                return {
                    "allowed": False,
                    "reason": "您已预约该班次，请勿重复预约",
                    "conflict_with": None,
                }

        if schedule:
            schedule_date = schedule.schedule_date

            if policy.per_user_per_day and policy.per_user_per_day > 0:
                day_count_result = await db.execute(
                    select(func.count(Appointment.id))
                    .join(Schedule, Appointment.schedule_id == Schedule.id)
                    .where(
                        and_(
                            Appointment.user_id == user_id,
                            Appointment.status.in_([1, 2]),
                            Schedule.schedule_date == schedule_date,
                        )
                    )
                )
                day_count = day_count_result.scalar() or 0
                if day_count >= policy.per_user_per_day:
                    return {
                        "allowed": False,
                        "reason": f"您今日已预约{day_count}次，每日最多可预约{policy.per_user_per_day}次",
                        "conflict_with": None,
                    }

            if policy.per_user_per_week and policy.per_user_per_week > 0:
                week_start = schedule_date - timedelta(days=schedule_date.weekday())
                week_end = week_start + timedelta(days=6)

                week_count_result = await db.execute(
                    select(func.count(Appointment.id))
                    .join(Schedule, Appointment.schedule_id == Schedule.id)
                    .where(
                        and_(
                            Appointment.user_id == user_id,
                            Appointment.status.in_([1, 2]),
                            Schedule.schedule_date >= week_start,
                            Schedule.schedule_date <= week_end,
                        )
                    )
                )
                week_count = week_count_result.scalar() or 0
                if week_count >= policy.per_user_per_week:
                    return {
                        "allowed": False,
                        "reason": f"您本周已预约{week_count}次，每周最多可预约{policy.per_user_per_week}次",
                        "conflict_with": None,
                    }

            if policy.conflict_overlap_time == "REJECT" and schedule.start_time and schedule.end_time:
                overlap_result = await db.execute(
                    select(Appointment, Schedule)
                    .join(Schedule, Appointment.schedule_id == Schedule.id)
                    .where(
                        and_(
                            Appointment.user_id == user_id,
                            Appointment.status.in_([1, 2]),
                            Schedule.schedule_date == schedule_date,
                            Schedule.id != shift_id,
                            Schedule.start_time < schedule.end_time,
                            Schedule.end_time > schedule.start_time,
                        )
                    )
                    .limit(1)
                )
                overlap_row = overlap_result.first()
                if overlap_row:
                    conflict_appointment, conflict_schedule = overlap_row
                    return {
                        "allowed": False,
                        "reason": (
                            "您在该时间段已有其他预约"
                            f"（{conflict_schedule.start_time.strftime('%H:%M')}"
                            f"-{conflict_schedule.end_time.strftime('%H:%M')}），时间冲突"
                        ),
                        "conflict_with": {
                            "appointment_id": conflict_appointment.id,
                            "schedule_id": conflict_schedule.id,
                            "start_time": str(conflict_schedule.start_time),
                            "end_time": str(conflict_schedule.end_time),
                        },
                    }

            if policy.conflict_same_type_same_day == "REJECT" and schedule.appointment_type:
                same_type_result = await db.execute(
                    select(Appointment, Schedule)
                    .join(Schedule, Appointment.schedule_id == Schedule.id)
                    .where(
                        and_(
                            Appointment.user_id == user_id,
                            Appointment.status.in_([1, 2]),
                            Schedule.schedule_date == schedule_date,
                            Schedule.appointment_type == schedule.appointment_type,
                            Schedule.id != shift_id,
                        )
                    )
                    .limit(1)
                )
                same_type_row = same_type_result.first()
                if same_type_row:
                    conflict_appointment, conflict_schedule = same_type_row
                    appointment_type_names = {
                        "normal": "普通门诊",
                        "expert": "专家门诊",
                        "urgent": "急诊",
                        "medical_insurance": "医保门诊",
                        "self_pay": "自费门诊",
                    }
                    type_name = appointment_type_names.get(
                        schedule.appointment_type, schedule.appointment_type
                    )
                    return {
                        "allowed": False,
                        "reason": f"您今日已预约{type_name}，同类型预约每日限一次",
                        "conflict_with": {
                            "appointment_id": conflict_appointment.id,
                            "schedule_id": conflict_schedule.id,
                            "appointment_type": conflict_schedule.appointment_type,
                        },
                    }

        return {"allowed": True, "reason": None, "conflict_with": None}

    @monitor_performance("check_capacity_limits")
    async def check_capacity_limits(
        self,
        db,
        shift_id: str,
        user_id: str,
        policy: RuleCapacityPolicy,
    ) -> Dict[str, Any]:
        if policy.total_capacity is not None and policy.total_capacity > 0:
            total_count = await db.execute(
                select(func.count(Appointment.id)).where(
                    and_(
                        Appointment.schedule_id == shift_id,
                        Appointment.status.in_([1, 2]),
                    )
                )
            )
            count = total_count.scalar() or 0

            if policy.overbooking_enabled and count >= policy.total_capacity + policy.overbooking_max:
                return {
                    "allowed": False,
                    "reason": f"该班次已约满（总容量{policy.total_capacity}，超额{policy.overbooking_max}）",
                    "waitlist_position": None,
                    "is_overbooking": False,
                }
            if not policy.overbooking_enabled and count >= policy.total_capacity:
                if policy.waitlist_enabled:
                    waitlist_pos = await self._calculate_waitlist_position(db, shift_id, user_id)
                    return {
                        "allowed": False,
                        "reason": f"该班次已约满（总容量{policy.total_capacity}），您的候补位置：第{waitlist_pos}位",
                        "waitlist_position": waitlist_pos,
                        "is_overbooking": False,
                    }
                return {
                    "allowed": False,
                    "reason": f"该班次已约满（总容量{policy.total_capacity}）",
                    "waitlist_position": None,
                    "is_overbooking": False,
                }

        if policy.per_user_capacity:
            user_count = await db.execute(
                select(func.count(Appointment.id)).where(
                    and_(
                        Appointment.schedule_id == shift_id,
                        Appointment.user_id == user_id,
                        Appointment.status.in_([1, 2]),
                    )
                )
            )
            count = user_count.scalar() or 0
            if count >= policy.per_user_capacity:
                return {
                    "allowed": False,
                    "reason": f"您已达到该班次的预约上限（{policy.per_user_capacity}次）",
                    "waitlist_position": None,
                    "is_overbooking": False,
                }

        return {
            "allowed": True,
            "reason": None,
            "waitlist_position": None,
            "is_overbooking": False,
        }

    def calculate_checkin_grace_period(
        self,
        appointment: Appointment,
        policy: RuleCheckinPolicy,
        current_time: datetime,
    ) -> Dict[str, Any]:
        checkin_close_at = appointment.checkin_close_at
        if not checkin_close_at:
            return {
                "in_grace_period": True,
                "is_late": False,
                "can_checkin": True,
                "suggested_status": "ON_TIME",
            }

        local_tz = pytz.timezone("Asia/Shanghai")
        if checkin_close_at.tzinfo is None:
            checkin_close_at = local_tz.localize(checkin_close_at)
        if current_time.tzinfo is None:
            current_time = local_tz.localize(current_time)

        grace_period_end = checkin_close_at + timedelta(seconds=policy.grace_period_sec)
        in_grace_period = current_time <= grace_period_end
        is_late = current_time > checkin_close_at
        suggested_status = (
            policy.after_grace_status or "LATE" if (not in_grace_period and is_late) else "ON_TIME"
        )

        return {
            "in_grace_period": in_grace_period,
            "is_late": is_late,
            "can_checkin": True,
            "suggested_status": suggested_status,
        }

    async def _calculate_waitlist_position(self, db, shift_id: str, user_id: str) -> int:
        result = await db.execute(
            select(WaitlistEntry.position).where(
                and_(
                    WaitlistEntry.schedule_id == shift_id,
                    WaitlistEntry.user_id == user_id,
                    WaitlistEntry.status == "WAITING",
                )
            )
        )
        position = result.scalar_one_or_none()
        return position if position is not None else -1
