from datetime import datetime, time, timedelta

import pytz
from sqlalchemy import select

from app.core.error_codes import ErrorCode
from app.core.events import EventType
from app.core.websocket import WSMessageType, notify_patient
from app.middleware.exception import BusinessError
from app.models.rule_set import AppointmentCheckin
from app.models.schedule import Schedule
from app.enums.appointment import CheckinMethod
from app.modules.appointments.common import APPOINTMENT_STATUS, AppointmentServiceBase, logger
from app.modules.rule_engine import RuleEngineService
from app.modules.settings.service import SettingsService
from app.utils.datetime import utc_now


class AppointmentFlowService(AppointmentServiceBase):
    async def sign_in(
        self,
        appointment_id: str,
        user_id: str | None = None,
        is_admin: bool = False,
        checkin_method: str = CheckinMethod.MANUAL,
        device_info: str | None = None,
        location_info: str | None = None,
        operator_id: str | None = None,
        operator_type: str | None = None,
    ):
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None

        try:
            if not is_admin and user_id and appointment.user_id != user_id:
                raise BusinessError("无权操作此预约", error_code=ErrorCode.PERMISSION_DENIED)
            if appointment.status != APPOINTMENT_STATUS["CONFIRMED"]:
                raise BusinessError("当前状态不可签到", error_code=ErrorCode.APPOINTMENT_INVALID_STATUS)

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
                    raise BusinessError(f"未到签到时间，请等待{minutes_until}分钟后再试", error_code=ErrorCode.CHECKIN_NOT_OPENED)
                if now > checkin_close:
                    raise BusinessError("已过签到时间，无法签到", error_code=ErrorCode.CHECKIN_WINDOW_CLOSED)
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
                            "morning": time(8, 0),
                            "afternoon": time(14, 0),
                            "evening": time(18, 0),
                        }
                        visit_time = time_slot_start_map.get(schedule.time_slot, time(8, 0))
                    visit_datetime = local_tz.localize(datetime.combine(schedule.schedule_date, visit_time))
                    sign_in_start = visit_datetime - timedelta(minutes=sign_in_advance_minutes)
                    sign_in_end = visit_datetime + timedelta(minutes=sign_in_late_minutes)
                    if now < sign_in_start:
                        minutes_until = int((sign_in_start - now).total_seconds() / 60)
                        raise BusinessError(f"未到签到时间，请等待{minutes_until}分钟后再试", error_code=ErrorCode.CHECKIN_NOT_OPENED)
                    if now > sign_in_end:
                        raise BusinessError("已过签到时间，无法签到", error_code=ErrorCode.CHECKIN_WINDOW_CLOSED)

            if appointment.rule_set_id:
                rule_engine_cls = self._compat("RuleEngineService", RuleEngineService)
                rule_engine = rule_engine_cls(self.db)
                checkin_policy = await rule_engine.get_checkin_policy_by_rule_set_id(appointment.rule_set_id)
                if checkin_policy and checkin_policy.max_times:
                    current_count = appointment.checkin_count or 0
                    if current_count >= checkin_policy.max_times:
                        raise BusinessError(f"已达到最大签到次数限制（{checkin_policy.max_times}次）", error_code=ErrorCode.CHECKIN_LIMIT_EXCEEDED)
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

            # 站内信通知（签到成功）—— 对齐 call_patient 的三渠道通知模式
            try:
                from app.modules.unified_message.compat import MessageServiceCompat as MessageService

                _signin_schedule = appointment.schedule
                _signin_time_slot = {
                    "morning": "上午",
                    "afternoon": "下午",
                    "evening": "晚间",
                }.get(_signin_schedule.time_slot, _signin_schedule.time_slot or "") if _signin_schedule else ""

                message_service = MessageService(self.db)
                await message_service.send_appointment_notification(
                    user_id=appointment.user_id,
                    user_type="patient",
                    title="签到成功",
                    content=f"您已成功签到，{appointment.doctor_name or '医生'}医生的预约，请耐心等待叫号。",
                    appointment_id=appointment.id,
                    template_variables={
                        "doctor_name": appointment.doctor_name or "医生",
                        "appointment_date": _signin_schedule.schedule_date.strftime("%Y年%m月%d日") if _signin_schedule else "",
                        "appointment_time": _signin_time_slot,
                    },
                )
            except Exception as exc:
                logger.warning(f"签到站内信通知发送失败: {exc}")

            # 微信订阅消息推送（签到成功）—— 模板配置存在才推送，避免噪音
            try:
                from app.middleware.tenant_context import get_current_tenant_id
                from app.models.user import User as _User
                from app.tasks.notification_task import _send_wechat_notification

                _signin_tenant_id = get_current_tenant_id()
                _signin_user_result = await self.db.execute(
                    select(_User).where(_User.id == appointment.user_id)
                )
                _signin_user = _signin_user_result.scalar_one_or_none()
                if _signin_user and _signin_user.openid:
                    _signin_schedule = appointment.schedule
                    _signin_queue = str(appointment.queue_number) if appointment.queue_number else ""
                    await _send_wechat_notification(
                        db=self.db,
                        tenant_id=_signin_tenant_id or appointment.tenant_id,
                        openid=_signin_user.openid,
                        template_id_config_key="checkin_success_template_id",
                        template_data={
                            "thing1": {"value": (appointment.doctor_name or "医生")[:20]},
                            "thing2": {"value": f"{_signin_queue}号"},
                            "thing3": {"value": "签到成功，请等待叫号"},
                        },
                        message_type="checkin_success",
                        title="签到成功",
                        user_id=appointment.user_id,
                        store_id=_signin_schedule.store_id if _signin_schedule else None,
                        related_id=appointment.id,
                        page=f"pages/appointment/detail?id={appointment.id}",
                    )
            except Exception as exc:
                logger.warning(f"签到微信推送失败（不影响主流程）: {exc}")

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
        appointment_id: str | None,
        checkin_method: str,
        device_info: str | None,
        location_info: str | None,
        operator_id: str | None,
        operator_type: str | None,
        status: str,
        fail_reason: str | None,
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
            raise BusinessError("只有已签到状态的预约才能取消签到", error_code=ErrorCode.APPOINTMENT_INVALID_STATUS)
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
            raise BusinessError("患者未签到", error_code=ErrorCode.APPOINTMENT_INVALID_STATUS)
        appointment.status = APPOINTMENT_STATUS["SEEING"]
        appointment.call_time = utc_now()
        await self.db.commit()
        await self.db.refresh(appointment)

        # 站内信通知（叫号）
        try:
            from app.modules.unified_message.compat import MessageServiceCompat as MessageService

            _call_schedule = appointment.schedule
            _call_queue = str(appointment.queue_number) if appointment.queue_number else ""
            _call_time_slot = {
                "morning": "上午",
                "afternoon": "下午",
                "evening": "晚间",
            }.get(_call_schedule.time_slot, _call_schedule.time_slot or "") if _call_schedule else ""

            message_service = MessageService(self.db)
            await message_service.send_appointment_notification(
                user_id=appointment.user_id,
                user_type="patient",
                title="叫号通知",
                content=f"您的排队号为{_call_queue}号，{appointment.doctor_name or '医生'}医生正在叫您，请前往诊室就诊。",
                appointment_id=appointment.id,
                template_variables={
                    "doctor_name": appointment.doctor_name or "医生",
                    "appointment_date": _call_schedule.schedule_date.strftime("%Y年%m月%d日") if _call_schedule else "",
                    "appointment_time": _call_time_slot,
                    "queue_number": _call_queue,
                },
            )
        except Exception as exc:
            logger.warning(f"叫号站内信通知发送失败: {exc}")

        # 微信订阅消息推送（叫号通知）
        try:
            from app.middleware.tenant_context import get_current_tenant_id
            from app.models.user import User as _User
            from app.tasks.notification_task import _send_wechat_notification

            _call_tenant_id = get_current_tenant_id()
            _call_user_result = await self.db.execute(
                select(_User).where(_User.id == appointment.user_id)
            )
            _call_user = _call_user_result.scalar_one_or_none()
            if _call_user and _call_user.openid:
                _call_schedule = appointment.schedule
                _call_queue = str(appointment.queue_number) if appointment.queue_number else ""
                await _send_wechat_notification(
                    db=self.db,
                    tenant_id=_call_tenant_id or appointment.tenant_id,
                    openid=_call_user.openid,
                    template_id_config_key="queue_call_template_id",
                    template_data={
                        "thing1": {"value": (appointment.doctor_name or "医生")[:20]},
                        "thing2": {"value": f"{_call_queue}号"},
                        "thing3": {"value": "请前往诊室就诊"},
                    },
                    message_type="queue_call",
                    title="叫号通知",
                    user_id=appointment.user_id,
                    store_id=_call_schedule.store_id if _call_schedule else None,
                    related_id=appointment.id,
                    page=f"pages/appointment/detail?id={appointment.id}",
                )
        except Exception as exc:
            logger.warning(f"叫号微信推送失败（不影响主流程）: {exc}")

        self._dispatch_email_event(EventType.CALL_PATIENT, appointment)
        return appointment

    async def complete(self, appointment_id: str):
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        if appointment.status not in [APPOINTMENT_STATUS["SIGNED"], APPOINTMENT_STATUS["SEEING"]]:
            raise BusinessError("只有已签到或就诊中状态的预约才能标记完成", error_code=ErrorCode.APPOINTMENT_INVALID_STATUS)
        appointment.status = APPOINTMENT_STATUS["COMPLETED"]
        appointment.complete_time = utc_now()
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

        # 满意度调查推送
        try:
            await message_service.send_appointment_notification(
                user_id=appointment.user_id,
                user_type="patient",
                title="满意度调查",
                content=f"您在{appointment.doctor_name}医生处的就诊已完成，请对本次就诊体验进行评价，您的反馈是我们改进的动力！",
                appointment_id=appointment.id,
            )
        except Exception as exc:
            logger.warning(f"满意度调查通知发送失败（不影响主流程）: {exc}")

        # 微信订阅消息推送（就诊完成）—— 模板配置存在才推送，避免噪音
        try:
            from app.middleware.tenant_context import get_current_tenant_id
            from app.models.user import User as _User
            from app.tasks.notification_task import _send_wechat_notification

            _complete_tenant_id = get_current_tenant_id()
            _complete_user_result = await self.db.execute(
                select(_User).where(_User.id == appointment.user_id)
            )
            _complete_user = _complete_user_result.scalar_one_or_none()
            if _complete_user and _complete_user.openid:
                _complete_schedule = appointment.schedule
                await _send_wechat_notification(
                    db=self.db,
                    tenant_id=_complete_tenant_id or appointment.tenant_id,
                    openid=_complete_user.openid,
                    template_id_config_key="appointment_completed_template_id",
                    template_data={
                        "thing1": {"value": (appointment.doctor_name or "医生")[:20]},
                        "thing2": {"value": "就诊已完成"},
                        "thing3": {"value": "感谢您的信任，祝您早日康复"},
                    },
                    message_type="visit_completed",
                    title="就诊完成",
                    user_id=appointment.user_id,
                    store_id=_complete_schedule.store_id if _complete_schedule else None,
                    related_id=appointment.id,
                    page=f"pages/appointment/detail?id={appointment.id}",
                )
        except Exception as exc:
            logger.warning(f"就诊完成微信推送失败（不影响主流程）: {exc}")

        self._dispatch_email_event(EventType.VISIT_COMPLETED, appointment)
        return appointment

    async def pass_number(self, appointment_id: str):
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        if appointment.status not in [APPOINTMENT_STATUS["SIGNED"], APPOINTMENT_STATUS["SEEING"]]:
            raise BusinessError("当前状态不可过号", error_code=ErrorCode.APPOINTMENT_INVALID_STATUS)
        appointment.status = APPOINTMENT_STATUS["EXPIRED"]
        await self.db.commit()
        await self.db.refresh(appointment)

        # 通知患者端过号
        try:
            patient_id = appointment.user_id or appointment.patient_id
            if patient_id:
                await notify_patient(
                    patient_id=patient_id,
                    message_type=WSMessageType.PATIENT_PASSED,
                    data={
                        "appointment_id": appointment.id,
                        "queue_number": appointment.queue_number,
                        "doctor_name": appointment.doctor_name,
                    },
                    tenant_id=appointment.tenant_id,
                )
        except Exception as exc:
            logger.warning(f"过号患者通知失败（不影响主流程）: {exc}")

        return appointment

    async def recall(self, appointment_id: str):
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        if appointment.status != APPOINTMENT_STATUS["EXPIRED"]:
            raise BusinessError("只有过号状态可以重新叫号", error_code=ErrorCode.APPOINTMENT_INVALID_STATUS)
        appointment.status = APPOINTMENT_STATUS["SEEING"]
        appointment.call_time = utc_now()
        await self.db.commit()
        await self.db.refresh(appointment)

        # 通知患者端重新叫号
        try:
            patient_id = appointment.user_id or appointment.patient_id
            if patient_id:
                await notify_patient(
                    patient_id=patient_id,
                    message_type=WSMessageType.PATIENT_RECALLED,
                    data={
                        "appointment_id": appointment.id,
                        "queue_number": appointment.queue_number,
                        "doctor_name": appointment.doctor_name,
                    },
                    tenant_id=appointment.tenant_id,
                )
        except Exception as exc:
            logger.warning(f"重新叫号患者通知失败（不影响主流程）: {exc}")

        return appointment

    async def mark_no_show(self, appointment_id: str):
        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None
        if appointment.status not in [APPOINTMENT_STATUS["CONFIRMED"], APPOINTMENT_STATUS["EXPIRED"]]:
            raise BusinessError("当前状态不可标记爽约", error_code=ErrorCode.APPOINTMENT_INVALID_STATUS)
        appointment.status = APPOINTMENT_STATUS["NO_SHOW"]
        await self.db.commit()
        await self.db.refresh(appointment)

        # 站内信通知（爽约）—— 爽约对患者是重大事件，必须告知
        try:
            from app.modules.unified_message.compat import MessageServiceCompat as MessageService

            message_service = MessageService(self.db)
            await message_service.send_appointment_notification(
                user_id=appointment.user_id,
                user_type="patient",
                title="爽约提醒",
                content=f"您预约的{appointment.doctor_name or '医生'}的号源因未按时就诊已被标记为爽约。如需重新预约，请前往小程序重新挂号。",
                appointment_id=appointment.id,
            )
        except Exception as exc:
            logger.warning(f"爽约站内信通知发送失败: {exc}")

        # 微信订阅消息推送（爽约）—— 模板配置存在才推送，避免噪音
        try:
            from app.middleware.tenant_context import get_current_tenant_id
            from app.models.user import User as _User
            from app.tasks.notification_task import _send_wechat_notification

            _noshow_tenant_id = get_current_tenant_id()
            _noshow_user_result = await self.db.execute(
                select(_User).where(_User.id == appointment.user_id)
            )
            _noshow_user = _noshow_user_result.scalar_one_or_none()
            if _noshow_user and _noshow_user.openid:
                _noshow_schedule = appointment.schedule
                await _send_wechat_notification(
                    db=self.db,
                    tenant_id=_noshow_tenant_id or appointment.tenant_id,
                    openid=_noshow_user.openid,
                    template_id_config_key="appointment_no_show_template_id",
                    template_data={
                        "thing1": {"value": (appointment.doctor_name or "医生")[:20]},
                        "thing2": {"value": "爽约"},
                        "thing3": {"value": "如需就诊请重新预约"},
                    },
                    message_type="no_show",
                    title="爽约提醒",
                    user_id=appointment.user_id,
                    store_id=_noshow_schedule.store_id if _noshow_schedule else None,
                    related_id=appointment.id,
                    page=f"pages/appointment/detail?id={appointment.id}",
                )
        except Exception as exc:
            logger.warning(f"爽约微信推送失败（不影响主流程）: {exc}")

        # WebSocket 实时通知（爽约）—— 与 pass_number/recall 一致，实时告知患者端
        try:
            patient_id = appointment.user_id or appointment.patient_id
            if patient_id:
                await notify_patient(
                    patient_id=patient_id,
                    message_type=WSMessageType.PATIENT_PASSED,
                    data={
                        "appointment_id": appointment.id,
                        "queue_number": appointment.queue_number,
                        "doctor_name": appointment.doctor_name,
                        "no_show": True,
                    },
                    tenant_id=appointment.tenant_id,
                )
        except Exception as exc:
            logger.warning(f"爽约患者实时通知失败（不影响主流程）: {exc}")

        self._dispatch_email_event(EventType.NO_SHOW, appointment)
        return appointment

    async def set_assistant_confirm_status(
        self,
        appointment_id: str,
        status: int,
        operator_id: str | None = None,
    ):
        """医助电话确认到店状态

        assistant_confirm_status: 0无需 1待联系 2已联系 3已确认到店时间。
        合法取值（2/3）由请求 Schema 校验，此处不再重复校验。
        note 不落库（appointments 无 note 列），仅由路由层回显。
        """
        from app.utils.audit import set_update_audit

        appointment = await self.get_by_id(appointment_id)
        if not appointment:
            return None

        appointment.assistant_confirm_status = status
        set_update_audit(appointment, operator_id)
        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment
