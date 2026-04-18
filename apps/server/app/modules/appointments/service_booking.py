from datetime import date, datetime, time, timedelta
import uuid
from typing import Optional
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from app.core.events import EventType
from app.core.redis import RedisCache
from app.models.appointment import Appointment
from app.models.blacklist import Blacklist
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.user import Patient
from app.modules.appointments.common import (
    ACTIVE_APPOINTMENT_STATUSES,
    APPOINTMENT_STATUS,
    AppointmentServiceBase,
    logger,
)
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

        if not rule_set:
            same_day_booking = await settings_service.get_value(
                "booking",
                "same_day_booking",
                True,
                store_id=store_id,
            )
            if schedule.schedule_date == date.today() and not same_day_booking:
                raise ValueError("当前不允许当天预约")

            advance_days = await settings_service.get_value("booking", "advance_days", 10, store_id=store_id)
            max_date = date.today() + timedelta(days=advance_days)
            if schedule.schedule_date > max_date:
                raise ValueError(f"预约日期不能超过{advance_days}天")

            blacklist = await self._get_active_blacklist(
                user_id=user_id,
                patient=patient,
                store_id=store_id,
            )
            if blacklist:
                reason = blacklist.reason or "您已被限制预约，请联系工作人员"
                raise ValueError(reason)

        user_lock_name = f"appointment:create:user:{user_id}"
        schedule_lock_name = f"appointment:create:{data.schedule_id}"
        try:
            redis_cache = self._compat("RedisCache", RedisCache)
            async with redis_cache.tenant_distributed_lock(
                user_lock_name,
                tenant_id=current_tenant_id,
                timeout=10,
                retry_times=5,
            ):
                if not rule_set:
                    per_day_limit = await settings_service.get_value("booking", "per_day_limit", 3, store_id=store_id)
                    today_count = await self._count_user_store_daily_appointments(user_id, store_id, schedule.schedule_date)
                    if today_count >= per_day_limit:
                        raise ValueError(f"当日预约已达上限（最多{per_day_limit}次）")

                    duplicate_same_day = await self.check_duplicate_same_day(
                        user_id=user_id,
                        patient_id=data.patient_id,
                        schedule_date=schedule.schedule_date,
                        time_slot=schedule.time_slot,
                    )
                    if duplicate_same_day:
                        raise ValueError("该就诊人同一天同一时段已有预约")

                    per_doctor_limit = await settings_service.get_value(
                        "booking",
                        "per_doctor_limit",
                        1,
                        store_id=store_id,
                    )
                    doctor_count = await self._count_user_doctor_active_appointments(user_id, schedule.doctor_id)
                    if doctor_count >= per_doctor_limit:
                        raise ValueError(f"同一医生预约已达上限（最多{per_doctor_limit}次）")

                async with redis_cache.tenant_distributed_lock(
                    schedule_lock_name,
                    tenant_id=current_tenant_id,
                    timeout=10,
                    retry_times=5,
                ):
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
                                Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
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

                    consultation_fee = await self._get_consultation_fee(
                        doctor_id=schedule.doctor_id,
                        store_id=schedule.store_id,
                        department_id=doctor.department_id if doctor else None,
                    )

                    if consultation_fee and consultation_fee > 0:
                        appointment_status = 0
                    else:
                        appointment_status = APPOINTMENT_STATUS["CONFIRMED"]

                    appointment = Appointment(
                        id=str(uuid.uuid4()),
                        appointment_no=appointment_no,
                        user_id=user_id,
                        patient_id=data.patient_id,
                        doctor_id=schedule.doctor_id,
                        schedule_id=data.schedule_id,
                        tenant_id=schedule.tenant_id,
                        queue_number=queue_number,
                        status=appointment_status,
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
                        payment_amount=consultation_fee,
                    )
                    set_create_audit(appointment, operator_id or user_id)
                    self.db.add(appointment)
                    schedule.booked_slots += 1
                    await self.db.commit()
                    await self.db.refresh(appointment)
        except RuntimeError as exc:
            logger.warning(f"预约创建获取锁失败: user_lock={user_lock_name}, schedule_lock={schedule_lock_name}, 错误: {exc}")
            raise ValueError("系统繁忙，请稍后重试")

        appointment.schedule = schedule

        # === 如果需要支付，准备支付参数 ===
        payment_params = None
        payment_param_error: Optional[str] = None
        if appointment.status == 0:  # 待支付
            payment_params, payment_param_error = await self._prepare_payment_params(
                appointment=appointment,
                schedule=schedule,
                user_openid=user.openid if user else None,
            )

        # === 发送消息通知 ===
        try:
            message_service_cls = self._compat("MessageService", MessageService)
            message_service = message_service_cls(self.db)
            time_slot_display = {
                "morning": "上午",
                "afternoon": "下午",
                "evening": "晚间",
            }.get(schedule.time_slot, schedule.time_slot)

            if appointment.status == 0:
                # 待支付状态
                content = (
                    f"您正在预约{appointment.doctor_name}医生，就诊日期："
                    f"{schedule.schedule_date.strftime('%Y年%m月%d日')} {time_slot_display}，排队号：{queue_number}号。"
                    f"诊费：{consultation_fee or 0}元。请完成支付以确认预约。"
                )
                title = "预约待支付"
            else:
                # 已确认
                content = (
                    f"您已成功预约{appointment.doctor_name}医生，就诊日期："
                    f"{schedule.schedule_date.strftime('%Y年%m月%d日')} {time_slot_display}，排队号：{queue_number}号。请按时到院签到。"
                )
                title = "预约成功"

            await message_service.send_appointment_notification(
                user_id=user_id,
                user_type="patient",
                title=title,
                content=content,
                appointment_id=appointment.id,
            )
        except Exception as exc:
            logger.warning(f"预约消息通知发送失败: {exc}")

        self._dispatch_email_event(EventType.APPOINTMENT_CREATED, appointment, schedule)

        # === 返回结果 ===
        if payment_params:
            # 需要支付，返回预约信息和支付参数
            return {
                "appointment": appointment,
                "payment_required": True,
                "payment_amount": float(appointment.payment_amount or 0),
                "payment_params": payment_params,
            }
        else:
            # 无需支付，或支付参数暂时未准备完成
            if appointment.status == 0:
                # 把 payment_param_error 暴露给前端，避免用户看不到任何提示就被卡在"无支付参数"页面。
                # None 表示业务合法 fallback（如缺 openid），有值表示后端调用支付服务时出错需要重试。
                return {
                    "appointment": appointment,
                    "payment_required": True,
                    "payment_amount": float(appointment.payment_amount or 0),
                    "payment_params": None,
                    "payment_param_error": payment_param_error,
                }
            return appointment

    async def _get_active_blacklist(
        self,
        user_id: str,
        patient: Patient,
        store_id: Optional[str],
    ) -> Optional[Blacklist]:
        conditions = [
            Blacklist.status == 1,
            or_(Blacklist.expire_at.is_(None), Blacklist.expire_at > datetime.now()),
            or_(Blacklist.store_id.is_(None), Blacklist.store_id == store_id),
        ]

        match_conditions = [Blacklist.user_id == user_id]
        if patient.phone:
            match_conditions.append(Blacklist.keyword == patient.phone)
        if patient.id_card:
            match_conditions.append(Blacklist.keyword == patient.id_card)

        result = await self.db.execute(
            select(Blacklist).where(and_(*conditions, or_(*match_conditions))).limit(1)
        )
        return result.scalar_one_or_none()

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
        redis_cache = self._compat("RedisCache", RedisCache)

        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        if not is_admin and appointment.user_id != user_id:
            raise ValueError("无权操作此预约")

        # 待支付状态（status=0）可以直接取消，无需退款
        if appointment.status == 0:
            async with redis_cache.tenant_distributed_lock(
                f"appointment:cancel:{appointment.id}", tenant_id=current_tenant_id, timeout=10
            ):
                appointment = await self.get_by_id(appointment_id)
                if not appointment:
                    return None

                # 竞态保护：reload 后若发现微信回调已先到（写入了 payment_transaction_id），
                # 转走"已支付取消 + 退款"流程，避免出现"取消成功但钱已扣"的资损。
                if appointment.status != 0:
                    if (
                        appointment.payment_transaction_id
                        and appointment.status in (
                            APPOINTMENT_STATUS["CONFIRMED"],
                            APPOINTMENT_STATUS["SIGNED"],
                        )
                    ):
                        logger.info(
                            "取消请求与支付回调竞态：回调先到，转走已支付退款流程: appointment_id=%s",
                            appointment.id,
                        )
                    else:
                        raise ValueError("预约状态已变更")
                else:
                    # 用条件 UPDATE 改 status=0 → CANCELLED，避免与并发回调互相覆盖。
                    # rowcount=0 表示在锁内 reload 后到 UPDATE 之间被回调抢先（极小窗口），
                    # 此时 reload 重判：若已支付则走退款，否则报错。
                    from sqlalchemy import update as _update

                    cancel_stmt = (
                        _update(Appointment)
                        .where(
                            Appointment.id == appointment.id,
                            Appointment.status == 0,
                        )
                        .values(
                            status=APPOINTMENT_STATUS["CANCELLED"],
                            cancel_time=datetime.now(),
                            cancel_reason=reason,
                        )
                    )
                    cancel_result = await self.db.execute(cancel_stmt)
                    if cancel_result.rowcount == 0:
                        await self.db.rollback()
                        appointment = await self.get_by_id(appointment_id)
                        if not (
                            appointment
                            and appointment.payment_transaction_id
                            and appointment.status in (
                                APPOINTMENT_STATUS["CONFIRMED"],
                                APPOINTMENT_STATUS["SIGNED"],
                            )
                        ):
                            raise ValueError("预约状态已变更")
                        logger.info(
                            "取消条件 UPDATE 失败，回调已落库，转走已支付退款流程: appointment_id=%s",
                            appointment_id,
                        )

                # 重新加载以便补审计字段并联动 schedule.booked_slots / 退款触发
                appointment = await self.get_by_id(appointment_id)
                set_update_audit(appointment, operator_id or user_id)

                schedule = appointment.schedule
                # 已支付分支：触发退款（条件：当前状态非 CANCELLED 且已有 transaction_id）
                if appointment.status != APPOINTMENT_STATUS["CANCELLED"] and (
                    appointment.payment_amount
                    and appointment.payment_amount > 0
                    and appointment.payment_transaction_id
                ):
                    needs_refund = True
                    appointment.status = APPOINTMENT_STATUS["CANCELLED"]
                    appointment.cancel_time = datetime.now()
                    appointment.cancel_reason = reason
                else:
                    needs_refund = False

                if schedule:
                    schedule.booked_slots = max(0, schedule.booked_slots - 1)

                if needs_refund:
                    await self._refund_paid_appointment_on_cancel(
                        appointment=appointment,
                        operator_id=operator_id or user_id,
                        reason=reason or "用户取消预约",
                    )

                await self.db.commit()

            await self.db.refresh(appointment)

            try:
                message_service_cls = self._compat("MessageService", MessageService)
                message_service = message_service_cls(self.db)
                await message_service.send_appointment_notification(
                    user_id=appointment.user_id,
                    user_type="patient",
                    title="预约已取消",
                    content=f"您的待支付预约已取消。",
                    appointment_id=appointment.id,
                )
            except Exception as exc:
                logger.warning(f"取消预约消息通知发送失败: {exc}")

            return appointment

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
                            "morning": time(8, 0),
                            "afternoon": time(14, 0),
                            "evening": time(18, 0),
                        }
                        visit_time = time_slot_start_map.get(schedule.time_slot, time(8, 0))
                    visit_datetime = datetime.combine(schedule.schedule_date, visit_time)
                    cancel_deadline = visit_datetime - timedelta(hours=cancel_hours)
                    if now > cancel_deadline:
                        raise ValueError(f"就诊前{cancel_hours}小时内不可取消预约")

        schedule = appointment.schedule
        lock_name = f"appointment:cancel:{appointment.schedule_id}" if schedule else f"appointment:cancel:{appointment_id}"

        async with redis_cache.tenant_distributed_lock(lock_name, tenant_id=current_tenant_id, timeout=10, retry_times=5):
            appointment = await self.get_by_id(appointment_id)
            if not appointment:
                return None
            if appointment.status not in [APPOINTMENT_STATUS["CONFIRMED"], APPOINTMENT_STATUS["SIGNED"]]:
                raise ValueError("当前状态不可取消")

            schedule = appointment.schedule

            # 已支付预约取消必须同步发起退款，避免「钱在商户账上、号源已释放」造成资损。
            # 全额退款；若退款 service / 微信失败立即抛错，确保不会出现「取消了但没退款」的中间态。
            needs_refund = bool(
                appointment.payment_amount
                and appointment.payment_amount > 0
                and appointment.payment_transaction_id
            )

            appointment.status = APPOINTMENT_STATUS["CANCELLED"]
            appointment.cancel_time = datetime.now()
            appointment.cancel_reason = reason
            set_update_audit(appointment, operator_id or user_id)
            if schedule:
                schedule.booked_slots = max(0, schedule.booked_slots - 1)

            if needs_refund:
                await self._refund_paid_appointment_on_cancel(
                    appointment=appointment,
                    operator_id=operator_id or user_id,
                    reason=reason or "用户取消预约",
                )

            await self.db.commit()

        if schedule:
            try:
                from app.modules.waitlist.service import WaitlistService

                waitlist_service = WaitlistService(self.db)
                await waitlist_service.auto_promote(schedule_id=appointment.schedule_id, reason="APPOINTMENT_CANCELLED")
            except Exception as exc:
                logger.warning(f"候补自动递补失败: {exc}")

        await self.db.refresh(appointment)

        try:
            message_service_cls = self._compat("MessageService", MessageService)
            message_service = message_service_cls(self.db)
            time_slot_display = ""
            if schedule:
                time_slot_display = {
                    "morning": "上午",
                    "afternoon": "下午",
                    "evening": "晚间",
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

    async def _get_consultation_fee(
        self,
        doctor_id: str,
        store_id: str,
        department_id: str,
    ) -> Optional[Decimal]:
        """查询诊费金额

        优先级：
        1. DoctorConsultationFee（医生级别）
        2. StoreFeeTemplate（门店级别）
        3. ConsultationFeeTemplate（全局默认）

        默认返回初诊金额。
        """
        from app.models.consultation_fee import DoctorConsultationFee, ConsultationFeeType, StoreFeeTemplate, ConsultationFeeTemplate
        from app.middleware.tenant_context import get_current_tenant_id

        tenant_id = get_current_tenant_id()

        # 1. 查询医生诊费配置（优先级最高）
        doctor_fee_stmt = (
            select(DoctorConsultationFee)
            .options(selectinload(DoctorConsultationFee.fee_type))
            .where(
                DoctorConsultationFee.doctor_id == doctor_id,
                DoctorConsultationFee.store_id == store_id,
                DoctorConsultationFee.status == 1,
            )
        )
        if tenant_id:
            # DoctorConsultationFee 没有 tenant_id 字段，需要 join 检查
            pass

        doctor_fee_result = await self.db.execute(doctor_fee_stmt)
        doctor_fees = list(doctor_fee_result.scalars().all())

        if doctor_fees:
            # 返回第一个有效的诊费配置的初诊金额
            for fee in doctor_fees:
                if fee.initial_fee and fee.initial_fee > 0:
                    return fee.initial_fee

        # 2. 查询门店诊费模板
        # 首先获取默认的诊费类型
        default_fee_type_stmt = select(ConsultationFeeType).where(
            ConsultationFeeType.store_id.is_(None),
            ConsultationFeeType.code == "default",
            ConsultationFeeType.status == 1,
        )
        default_fee_type_result = await self.db.execute(default_fee_type_stmt)
        default_fee_type = default_fee_type_result.scalar_one_or_none()

        if default_fee_type:
            # 查询门店级别的模板
            store_template_stmt = select(StoreFeeTemplate).where(
                StoreFeeTemplate.store_id == store_id,
                StoreFeeTemplate.fee_type_id == default_fee_type.id,
                StoreFeeTemplate.status == 1,
            )
            store_template_result = await self.db.execute(store_template_stmt)
            store_template = store_template_result.scalar_one_or_none()

            if store_template and store_template.initial_fee and store_template.initial_fee > 0:
                return store_template.initial_fee

            # 3. 查询全局默认模板
            global_template_stmt = select(ConsultationFeeTemplate).where(
                ConsultationFeeTemplate.fee_type_id == default_fee_type.id,
                ConsultationFeeTemplate.status == 1,
            )
            global_template_result = await self.db.execute(global_template_stmt)
            global_template = global_template_result.scalar_one_or_none()

            if global_template and global_template.initial_fee and global_template.initial_fee > 0:
                return global_template.initial_fee

        # 未找到有效诊费配置
        return Decimal("0")

    async def _prepare_payment_params(
        self,
        appointment: Appointment,
        schedule: Schedule,
        user_openid: Optional[str] = None,
    ) -> tuple[Optional[dict], Optional[str]]:
        """准备支付参数

        返回 (payment_params, error_code)：
        - openid 缺失等业务合法 fallback 场景，返回 (None, None)，前端可由"重新发起支付"接口补拉。
        - PaymentService 调用异常视为可恢复错误：返回 (None, error_code)，由调用方写入响应供前端提示，
          同时以 logger.exception 全栈上报便于监控告警。
        - 不再静默吞掉异常 — 任何错误都必须有明确反馈，避免"预约已落库占号但用户拿不到支付参数"。
        """
        if not user_openid:
            logger.warning(
                "预约创建时缺少用户 openid，跳过直出支付参数: appointment_id=%s",
                appointment.id,
            )
            return None, None

        try:
            from app.modules.payments.service import PaymentService

            payment_service = PaymentService(self.db)
            params = await payment_service.create_payment_order(
                appointment_id=appointment.id,
                openid=user_openid,
                miniapp_instance_id=appointment.payment_miniapp_instance_id,
            )
            return params, None
        except ValueError as exc:
            # ValueError = 业务校验错误（如配置缺失、金额无效）— 用户重试无效，需明确反馈
            logger.exception(
                "预约创建后生成支付参数失败(业务错误): appointment_id=%s, store_id=%s",
                appointment.id,
                schedule.store_id,
            )
            return None, f"payment_config_error: {exc}"
        except Exception:
            # 其它异常（网络、微信下单失败等）— 可重试
            logger.exception(
                "预约创建后生成支付参数失败(系统错误): appointment_id=%s, store_id=%s",
                appointment.id,
                schedule.store_id,
            )
            return None, "payment_temporary_error"

    async def _refund_paid_appointment_on_cancel(
        self,
        appointment: Appointment,
        operator_id: str,
        reason: str,
    ) -> None:
        """已支付预约在取消时同事务发起全额退款。

        - 创建 RefundRecord(pending) → 调微信 → 标记 processing/failed
        - 不在此处 commit；由调用方 cancel() 统一 commit，确保「取消 + 退款单」原子性
        - 微信调用失败抛异常 → 上层事务回滚，预约不会进入 CANCELLED 状态，避免资损
        """
        from sqlalchemy import select as _select

        from app.infrastructure.payments.wechat_pay_service import WeChatPayService
        from app.models.miniapp_platform import PaymentProfile
        from app.modules.refunds.service import RefundService

        refund_service = RefundService(self.db)
        refund_record = await refund_service.create_refund(
            appointment_id=appointment.id,
            refund_amount=appointment.payment_amount,
            refund_reason=reason,
            operator_id=operator_id,
        )

        if not refund_record.payment_profile_id:
            raise ValueError("预约缺少支付配置快照，无法发起退款")

        profile_result = await self.db.execute(
            _select(PaymentProfile).where(PaymentProfile.id == refund_record.payment_profile_id)
        )
        profile = profile_result.scalar_one_or_none()
        if not profile:
            raise ValueError("退款关联的支付配置不存在")

        wx_service = WeChatPayService(profile)
        out_trade_no, transaction_id = await refund_service.ensure_refund_payment_reference(
            refund_record
        )

        wx_result = await wx_service.create_refund(
            out_trade_no=out_trade_no,
            out_refund_no=refund_record.refund_no,
            total=refund_record.original_amount,
            refund=refund_record.refund_amount,
            reason=refund_record.refund_reason or "",
            notify_url=profile.refund_notify_url or profile.notify_url or "",
            transaction_id=transaction_id,
        )

        refund_record.status = "processing"
        if wx_result.get("refund_id"):
            refund_record.wx_refund_id = wx_result.get("refund_id")
        await refund_service.sync_appointment_refund_state(refund_record.appointment_id)
