from datetime import date, datetime, time, timedelta
import uuid
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.core.events import EventType
from app.core.redis import RedisCache
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.user import Patient
from app.modules.appointments.common import APPOINTMENT_STATUS, AppointmentServiceBase, logger
from app.schemas.appointment import AppointmentCreate
from app.modules.messages.service_messages import MessageService
from app.modules.rule_engine import RuleEngineService
from app.modules.settings.service import SettingsService
from app.utils.audit import set_create_audit, set_update_audit


class AppointmentBookingService(AppointmentServiceBase):
    async def create(self, user_id: str, data: AppointmentCreate, operator_id: Optional[str] = None) -> Appointment:
        # 获取当前租户
        from app.middleware.tenant_context import get_current_tenant_id
        from app.models.user import User

        current_tenant_id = get_current_tenant_id()

        # 配额检查
        from app.common.quota import check_quota
        await check_quota(current_tenant_id, "appointments", self.db)

        schedule_result = await self.db.execute(
            select(Schedule)
            .options(selectinload(Schedule.doctor).selectinload(Doctor.department))
            .where(Schedule.id == data.schedule_id)
        )
        schedule = schedule_result.scalar_one_or_none()
        if not schedule:
            raise ValueError("排班不存在")
        if schedule.status != 1:
            raise ValueError("该排班已停诊")
        if schedule.booked_slots >= schedule.total_slots:
            raise ValueError("号源已满")

        # 租户一致性校验：排班必须属于当前租户
        if current_tenant_id and schedule.tenant_id != current_tenant_id:
            raise ValueError("排班不属于当前租户")

        if schedule.template_id is not None:
            is_rest_day = await self._check_rest_day(schedule.schedule_date, schedule.store_id, schedule.doctor_id)
            if is_rest_day:
                raise ValueError("该日期为休息日，无法预约")

        settings_service_cls = self._compat("SettingsService", SettingsService)
        settings_service = settings_service_cls(self.db)
        store_id = schedule.store_id
        rule_engine_cls = self._compat("RuleEngineService", RuleEngineService)
        rule_engine = rule_engine_cls(self.db)
        book_result = await rule_engine.check_action_window(schedule, "BOOK")
        if not book_result["allowed"] and book_result["fail_policy"] == "REJECT":
            raise ValueError(book_result["message"])

        checkin_result = await rule_engine.check_action_window(schedule, "CHECKIN")
        cancel_result = await rule_engine.check_action_window(schedule, "CANCEL")
        rule_set = None
        booking_policy = None
        capacity_policy = None
        if schedule.shift_type_id:
            rule_set = await rule_engine.get_applicable_rule_set(schedule.shift_type_id)
            if rule_set:
                booking_policy = await rule_engine.get_booking_policy(schedule.shift_type_id)
                capacity_policy = await rule_engine.get_capacity_policy(schedule.shift_type_id)

        if booking_policy:
            conflict_result = await rule_engine.check_booking_conflicts(
                db=self.db,
                shift_id=data.schedule_id,
                user_id=user_id,
                policy=booking_policy,
                booking_time=datetime.now(),
                schedule=schedule,
            )
            if not conflict_result["allowed"]:
                raise ValueError(conflict_result["reason"])

        capacity_check_needed = capacity_policy is not None
        if not rule_set:
            advance_days = await settings_service.get_value("booking", "advance_days", 10, store_id=store_id)
            max_date = date.today() + timedelta(days=advance_days)
            if schedule.schedule_date > max_date:
                raise ValueError(f"预约日期不能超过{advance_days}天")

            per_day_limit = await settings_service.get_value("booking", "per_day_limit", 3, store_id=store_id)
            today_count = await self._count_user_store_daily_appointments(user_id, store_id, schedule.schedule_date)
            if today_count >= per_day_limit:
                raise ValueError(f"当日预约已达上限（最多{per_day_limit}次）")

        # 租户一致性校验：获取用户并验证租户
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user and user.tenant_id != current_tenant_id:
            raise ValueError("用户不属于当前租户")

        patient_result = await self.db.execute(
            select(Patient).where(Patient.id == data.patient_id, Patient.user_id == user_id)
        )
        patient = patient_result.scalar_one_or_none()
        if not patient:
            raise ValueError("就诊人不存在")
        # 租户一致性校验：患者必须属于当前租户
        if current_tenant_id and patient.tenant_id != current_tenant_id:
            raise ValueError("就诊人不属于当前租户")

        lock_name = f"appointment:create:{data.schedule_id}"
        try:
            redis_cache = self._compat("RedisCache", RedisCache)
            async with redis_cache.tenant_distributed_lock(lock_name, tenant_id=current_tenant_id, timeout=10, retry_times=5):
                if capacity_check_needed and capacity_policy:
                    capacity_result = await rule_engine.check_capacity_limits(
                        db=self.db,
                        shift_id=data.schedule_id,
                        user_id=user_id,
                        policy=capacity_policy,
                    )
                    if not capacity_result["allowed"]:
                        raise ValueError(capacity_result["reason"])

                existing = await self.db.execute(
                    select(Appointment).where(
                        and_(
                            Appointment.patient_id == data.patient_id,
                            Appointment.schedule_id == data.schedule_id,
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
                if existing.scalar_one_or_none():
                    raise ValueError("该就诊人已预约此时段")

                schedule_refresh = await self.db.execute(select(Schedule).where(Schedule.id == data.schedule_id))
                schedule_current = schedule_refresh.scalar_one_or_none()
                if schedule_current and schedule_current.booked_slots >= schedule_current.total_slots:
                    raise ValueError("号源已满")

                appointment_no = f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}"
                queue_result = await self.db.execute(
                    select(func.max(Appointment.queue_number)).where(Appointment.schedule_id == data.schedule_id)
                )
                max_queue = queue_result.scalar() or 0
                queue_number = max_queue + 1

                doctor = schedule.doctor
                appointment = Appointment(
                    id=str(uuid.uuid4()),
                    appointment_no=appointment_no,
                    user_id=user_id,
                    patient_id=data.patient_id,
                    doctor_id=schedule.doctor_id,
                    schedule_id=data.schedule_id,
                    tenant_id=schedule.tenant_id,
                    queue_number=queue_number,
                    status=APPOINTMENT_STATUS["CONFIRMED"],
                    symptom_description=data.symptom_description,
                    patient_name=patient.name,
                    patient_phone=patient.phone,
                    doctor_name=doctor.name if doctor else None,
                    doctor_title=doctor.title if doctor else None,
                    department_name=doctor.department.name if doctor and doctor.department else None,
                    rule_set_id=rule_set.id if rule_set else None,
                    book_open_at=book_result["open_at"],
                    book_close_at=book_result["close_at"],
                    checkin_open_at=checkin_result["open_at"],
                    checkin_close_at=checkin_result["close_at"],
                    cancel_open_at=cancel_result["open_at"],
                    cancel_close_at=cancel_result["close_at"],
                    checkin_count=0,
                )
                set_create_audit(appointment, operator_id or user_id)
                self.db.add(appointment)
                schedule.booked_slots += 1
                await self.db.commit()
                await self.db.refresh(appointment)
        except RuntimeError as exc:
            logger.warning(f"预约创建获取锁失败: {lock_name}, 错误: {exc}")
            raise ValueError("系统繁忙，请稍后重试")

        appointment.schedule = schedule
        try:
            message_service_cls = self._compat("MessageService", MessageService)
            message_service = message_service_cls(self.db)
            time_slot_display = {
                "AM": "上午",
                "PM": "下午",
                "morning": "上午",
                "afternoon": "下午",
                "evening": "晚间",
                "NIGHT": "夜间",
            }.get(schedule.time_slot, schedule.time_slot)
            await message_service.send_appointment_notification(
                user_id=user_id,
                user_type="patient",
                title="预约成功",
                content=(
                    f"您已成功预约{appointment.doctor_name}医生，就诊日期："
                    f"{schedule.schedule_date.strftime('%Y年%m月%d日')} {time_slot_display}，排队号：{queue_number}号。请按时到院签到。"
                ),
                appointment_id=appointment.id,
            )
        except Exception as exc:
            logger.warning(f"预约成功消息通知发送失败: {exc}")

        self._dispatch_email_event(EventType.APPOINTMENT_CREATED, appointment, schedule)
        return appointment

    async def cancel(
        self,
        appointment_id: str,
        user_id: str,
        reason: Optional[str] = None,
        is_admin: bool = False,
        operator_id: Optional[str] = None,
    ) -> Optional[Appointment]:
        from app.middleware.tenant_context import get_current_tenant_id
        current_tenant_id = get_current_tenant_id()

        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        if not is_admin and appointment.user_id != user_id:
            raise ValueError("无权操作此预约")
        if appointment.status not in [APPOINTMENT_STATUS["CONFIRMED"], APPOINTMENT_STATUS["SIGNED"]]:
            raise ValueError("当前状态不可取消")

        if not is_admin:
            import pytz

            local_tz = pytz.timezone("Asia/Shanghai")
            now = datetime.now(local_tz)
            if appointment.cancel_open_at and appointment.cancel_close_at:
                if now < appointment.cancel_open_at:
                    raise ValueError("未到取消时间窗口")
                if now > appointment.cancel_close_at:
                    raise ValueError("已过取消时间窗口，无法取消预约")
            else:
                settings_service_cls = self._compat("SettingsService", SettingsService)
                settings_service = settings_service_cls(self.db)
                cancel_hours = await settings_service.get_value("booking", "cancel_hours", 2)
                schedule = appointment.schedule
                if schedule and cancel_hours > 0:
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
                    visit_datetime = datetime.combine(schedule.schedule_date, visit_time)
                    cancel_deadline = visit_datetime - timedelta(hours=cancel_hours)
                    if now > cancel_deadline:
                        raise ValueError(f"就诊前{cancel_hours}小时内不可取消预约")

        schedule = appointment.schedule
        lock_name = f"appointment:cancel:{appointment.schedule_id}" if schedule else f"appointment:cancel:{appointment_id}"

        redis_cache = self._compat("RedisCache", RedisCache)
        async with redis_cache.tenant_distributed_lock(lock_name, tenant_id=current_tenant_id, timeout=10, retry_times=5):
            appointment = await self.get_by_id(appointment_id)
            if not appointment:
                return None
            if appointment.status not in [APPOINTMENT_STATUS["CONFIRMED"], APPOINTMENT_STATUS["SIGNED"]]:
                raise ValueError("当前状态不可取消")

            schedule = appointment.schedule
            appointment.status = APPOINTMENT_STATUS["CANCELLED"]
            appointment.cancel_time = datetime.now()
            appointment.cancel_reason = reason
            set_update_audit(appointment, operator_id or user_id)
            if schedule:
                schedule.booked_slots = max(0, schedule.booked_slots - 1)
            await self.db.commit()

        if schedule:
            try:
                from app.modules.waitlist.service import WaitlistService

                waitlist_service = WaitlistService(self.db)
                await waitlist_service.auto_promote(schedule_id=appointment.schedule_id, reason="APPOINTMENT_CANCELLED")
            except Exception as exc:
                print(f"候补自动递补失败: {exc}")

        await self.db.refresh(appointment)

        try:
            message_service_cls = self._compat("MessageService", MessageService)
            message_service = message_service_cls(self.db)
            time_slot_display = ""
            if schedule:
                time_slot_display = {
                    "AM": "上午",
                    "PM": "下午",
                    "morning": "上午",
                    "afternoon": "下午",
                    "evening": "晚间",
                    "NIGHT": "夜间",
                }.get(schedule.time_slot, schedule.time_slot)
            cancel_reason_text = f"，取消原因：{reason}" if reason else ""
            schedule_date_str = schedule.schedule_date.strftime("%Y年%m月%d日") if schedule else ""
            await message_service.send_appointment_notification(
                user_id=appointment.user_id,
                user_type="patient",
                title="预约已取消",
                content=f"您预约的{appointment.doctor_name}医生（{schedule_date_str} {time_slot_display}）已取消{cancel_reason_text}。",
                appointment_id=appointment.id,
            )
        except Exception as exc:
            logger.warning(f"取消预约消息通知发送失败: {exc}")

        self._dispatch_email_event(EventType.APPOINTMENT_CANCELLED, appointment, schedule)
        return appointment
