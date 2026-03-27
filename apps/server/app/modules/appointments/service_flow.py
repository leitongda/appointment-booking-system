from datetime import date, datetime, time, timedelta
from typing import Optional

import pytz
from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from app.core.events import EventType
from app.models.rule_set import AppointmentCheckin
from app.models.schedule import Schedule
from app.modules.appointments.common import APPOINTMENT_STATUS, AppointmentServiceBase, logger
from app.modules.messages.service_messages import MessageService
from app.modules.rule_engine import RuleEngineService
from app.modules.settings.service import SettingsService


class AppointmentFlowService(AppointmentServiceBase):
    async def sign_in(
        self,
        appointment_id: str,
        user_id: Optional[str] = None,
        is_admin: bool = False,
        checkin_method: str = "MANUAL",
        device_info: Optional[str] = None,
        location_info: Optional[str] = None,
        operator_id: Optional[str] = None,
        operator_type: Optional[str] = None,
    ):
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None

        try:
            if not is_admin and user_id and appointment.user_id != user_id:
                raise ValueError("无权操作此预约")
            if appointment.status != APPOINTMENT_STATUS["CONFIRMED"]:
                raise ValueError("当前状态不可签到")

            local_tz = pytz.timezone("Asia/Shanghai")
            now = datetime.now(local_tz)
            if appointment.checkin_open_at and appointment.checkin_close_at:
                checkin_open = appointment.checkin_open_at
                checkin_close = appointment.checkin_close_at
                if checkin_open.tzinfo is None:
                    checkin_open = local_tz.localize(checkin_open)
                if checkin_close.tzinfo is None:
                    checkin_close = local_tz.localize(checkin_close)
                if now < checkin_open:
                    minutes_until = int((checkin_open - now).total_seconds() / 60)
                    raise ValueError(f"未到签到时间，请等待{minutes_until}分钟后再试")
                if now > checkin_close:
                    raise ValueError("已过签到时间，无法签到")
            else:
                stmt = select(Schedule).where(Schedule.id == appointment.schedule_id)
                result = await self.db.execute(stmt)
                schedule = result.scalar_one_or_none()
                if schedule:
                    settings_service_cls = self._compat("SettingsService", SettingsService)
                    settings_service = settings_service_cls(self.db)
                    settings = await settings_service.get_booking_settings(store_id=schedule.store_id)
                    sign_in_advance_minutes = settings.get("signInAdvanceMinutes", 30)
                    sign_in_late_minutes = settings.get("signInLateMinutes", 30)
                    if schedule.start_time:
                        visit_time = schedule.start_time
                    else:
                        time_slot_start_map = {
                            "AM": time(8, 0),
                            "PM": time(14, 0),
                            "morning": time(8, 0),
                            "afternoon": time(14, 0),
                            "evening": time(18, 0),
                            "NIGHT": time(18, 0),
                        }
                        visit_time = time_slot_start_map.get(schedule.time_slot, time(8, 0))
                    visit_datetime = local_tz.localize(datetime.combine(schedule.schedule_date, visit_time))
                    sign_in_start = visit_datetime - timedelta(minutes=sign_in_advance_minutes)
                    sign_in_end = visit_datetime + timedelta(minutes=sign_in_late_minutes)
                    if now < sign_in_start:
                        minutes_until = int((sign_in_start - now).total_seconds() / 60)
                        raise ValueError(f"未到签到时间，请等待{minutes_until}分钟后再试")
                    if now > sign_in_end:
                        raise ValueError("已过签到时间，无法签到")

            if appointment.rule_set_id:
                rule_engine_cls = self._compat("RuleEngineService", RuleEngineService)
                rule_engine = rule_engine_cls(self.db)
                checkin_policy = await rule_engine.get_checkin_policy_by_rule_set_id(appointment.rule_set_id)
                if checkin_policy and checkin_policy.max_times:
                    current_count = appointment.checkin_count or 0
                    if current_count >= checkin_policy.max_times:
                        raise ValueError(f"已达到最大签到次数限制（{checkin_policy.max_times}次）")
                if checkin_policy:
                    rule_engine.calculate_checkin_grace_period(
                        appointment=appointment,
                        policy=checkin_policy,
                        current_time=now,
                    )

            appointment.status = APPOINTMENT_STATUS["SIGNED"]
            appointment.sign_in_time = now
            appointment.checkin_count = (appointment.checkin_count or 0) + 1

            await self._create_checkin_log(
                appointment_id=appointment.id,
                checkin_method=checkin_method,
                device_info=device_info,
                location_info=location_info,
                operator_id=operator_id,
                operator_type=operator_type,
                status="SUCCESS",
                fail_reason=None,
            )

            await self.db.commit()
            await self.db.refresh(appointment)
            self._dispatch_email_event(EventType.CHECKIN, appointment)
            return appointment
        except Exception as exc:
            await self._create_checkin_log(
                appointment_id=appointment.id if appointment else None,
                checkin_method=checkin_method,
                device_info=device_info,
                location_info=location_info,
                operator_id=operator_id,
                operator_type=operator_type,
                status="FAILED",
                fail_reason=str(exc),
            )
            raise

    async def _create_checkin_log(
        self,
        appointment_id: Optional[str],
        checkin_method: str,
        device_info: Optional[str],
        location_info: Optional[str],
        operator_id: Optional[str],
        operator_type: Optional[str],
        status: str,
        fail_reason: Optional[str],
    ):
        if not appointment_id:
            return
        checkin_log = AppointmentCheckin(
            appointment_id=appointment_id,
            checkin_method=checkin_method,
            device_info=device_info,
            location_info=location_info,
            operator_id=operator_id,
            operator_type=operator_type,
            status=status,
            fail_reason=fail_reason,
        )
        self.db.add(checkin_log)
        await self.db.flush()

    async def cancel_sign_in(self, appointment_id: str):
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        if appointment.status != APPOINTMENT_STATUS["SIGNED"]:
            raise ValueError("只有已签到状态的预约才能取消签到")
        appointment.status = APPOINTMENT_STATUS["CONFIRMED"]
        appointment.sign_in_time = None
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment

    async def call_patient(self, appointment_id: str):
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        if appointment.status != APPOINTMENT_STATUS["SIGNED"]:
            raise ValueError("患者未签到")
        appointment.status = APPOINTMENT_STATUS["SEEING"]
        appointment.call_time = datetime.now()
        await self.db.commit()
        await self.db.refresh(appointment)
        self._dispatch_email_event(EventType.CALL_PATIENT, appointment)
        return appointment

    async def complete(self, appointment_id: str):
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        appointment.status = APPOINTMENT_STATUS["COMPLETED"]
        appointment.complete_time = datetime.now()
        await self.db.commit()
        await self.db.refresh(appointment)
        try:
            message_service_cls = self._compat("MessageService", MessageService)
            message_service = message_service_cls(self.db)
            await message_service.send_appointment_notification(
                user_id=appointment.user_id,
                user_type="patient",
                title="就诊完成",
                content=f"您在{appointment.doctor_name}医生处的就诊已完成。感谢您的信任，祝您早日康复！",
                appointment_id=appointment.id,
            )
        except Exception as exc:
            logger.warning(f"就诊完成消息通知发送失败: {exc}")
        self._dispatch_email_event(EventType.VISIT_COMPLETED, appointment)
        return appointment

    async def pass_number(self, appointment_id: str):
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        if appointment.status not in [APPOINTMENT_STATUS["SIGNED"], APPOINTMENT_STATUS["SEEING"]]:
            raise ValueError("当前状态不可过号")
        appointment.status = APPOINTMENT_STATUS["EXPIRED"]
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment

    async def recall(self, appointment_id: str):
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        if appointment.status != APPOINTMENT_STATUS["EXPIRED"]:
            raise ValueError("只有过号状态可以重新叫号")
        appointment.status = APPOINTMENT_STATUS["SEEING"]
        appointment.call_time = datetime.now()
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment

    async def mark_no_show(self, appointment_id: str):
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        if appointment.status not in [APPOINTMENT_STATUS["CONFIRMED"], APPOINTMENT_STATUS["EXPIRED"]]:
            raise ValueError("当前状态不可标记爽约")
        appointment.status = APPOINTMENT_STATUS["CLOSED"]
        await self.db.commit()
        await self.db.refresh(appointment)
        self._dispatch_email_event(EventType.NO_SHOW, appointment)
        return appointment
