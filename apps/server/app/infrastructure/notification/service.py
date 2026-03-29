"""通知服务"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.user import User, Patient
from app.modules.settings.service import SettingsService
from app.core.events import dispatch_event_email, EventType


class NotificationService:
    """通知服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def notify_suspend(self, schedule_id: str, reason: str = None) -> dict:
        """
        停诊通知
        - 查找该排班下所有未完成的预约
        - 发送停诊通知（短信 + 小程序消息）
        """
        # 查找排班和相关预约
        schedule_result = await self.db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        schedule = schedule_result.scalar_one_or_none()

        if not schedule:
            return {"notified_count": 0, "message": "排班不存在"}

        # 查找该排班下的有效预约（状态：待就诊、已签到、候诊）
        appointments_result = await self.db.execute(
            select(Appointment)
            .where(
                and_(
                    Appointment.schedule_id == schedule_id,
                    Appointment.status.in_([1, 2, 3])  # 已预约、已签到、候诊中
                )
            )
        )
        appointments = appointments_result.scalars().all()

        if not appointments:
            return {"notified_count": 0, "message": "该排班下无需通知的预约"}

        # 收集需要通知的用户
        notified_users = []
        failed_users = []

        for appointment in appointments:
            # 获取用户信息
            patient_result = await self.db.execute(
                select(Patient).where(Patient.id == appointment.patient_id)
            )
            patient = patient_result.scalar_one_or_none()

            if patient and patient.phone:
                try:
                    # 发送短信通知
                    await self._send_sms_suspend_notice(
                        phone=patient.phone,
                        patient_name=patient.name,
                        doctor_name=schedule.doctor.name if schedule.doctor else "医生",
                        schedule_date=str(schedule.schedule_date),
                        time_slot=schedule.time_slot,
                        reason=reason
                    )
                    notified_users.append({
                        "patient_id": patient.id,
                        "name": patient.name,
                        "phone": patient.phone,
                        "appointment_no": appointment.appointment_no
                    })
                except Exception as e:
                    failed_users.append({
                        "patient_id": patient.id,
                        "name": patient.name,
                        "error": str(e)
                    })

        # 邮件事件钩子：停诊通知
        try:
            time_slot_map = {'morning': '上午', 'afternoon': '下午', 'evening': '晚上'}
            dispatch_event_email(
                store_id=schedule.store_id,
                event_type=EventType.SCHEDULE_SUSPENDED,
                context={
                    "doctor_name": schedule.doctor.name if schedule.doctor else "",
                    "department_name": "",
                    "appointment_date": str(schedule.schedule_date) if schedule.schedule_date else "",
                    "appointment_time": time_slot_map.get(schedule.time_slot, schedule.time_slot or ""),
                    "appointment_no": "",
                    "patient_name": f"共 {len(appointments)} 位患者受影响",
                },
            )
        except Exception:
            pass  # fire-and-forget

        return {
            "notified_count": len(notified_users),
            "failed_count": len(failed_users),
            "notified_users": notified_users,
            "failed_users": failed_users,
            "message": f"已通知 {len(notified_users)} 位患者"
        }

    async def _send_sms_suspend_notice(
        self,
        phone: str,
        patient_name: str,
        doctor_name: str,
        schedule_date: str,
        time_slot: str,
        reason: str = None
    ):
        """发送停诊短信通知"""
        settings_service = SettingsService(self.db)
        sms_config = await settings_service.get_sms_config()

        provider = sms_config.get('smsProvider', 'aliyun')
        access_key_id = sms_config.get('accessKeyId', '')
        access_key_secret = sms_config.get('accessKeySecret', '')
        sign_name = sms_config.get('signName', '')

        if not access_key_id or not access_key_secret:
            # 短信配置不完整，记录日志但不抛出异常
            logger.warning(f"[SMS] 短信配置不完整，跳过发送: {phone}")
            return

        time_slot_map = {'morning': '上午', 'afternoon': '下午', 'evening': '晚上'}
        time_slot_text = time_slot_map.get(time_slot, time_slot)

        # 构建短信内容
        content = f"【停诊通知】{patient_name}您好，您预约的{schedule_date} {time_slot_text} {doctor_name}门诊因故停诊"
        if reason:
            content += f"，原因：{reason}"
        content += "。请您重新预约，给您带来不便敬请谅解。"

        # 这里可以根据不同的短信服务商调用不同的API
        # 目前只是记录日志，实际项目中需要接入短信服务商SDK
        logger.info(f"[SMS] 发送停诊通知: {phone} - {content}")

        # TODO: 接入阿里云/腾讯云短信API
        # if provider == 'aliyun':
        #     await self._send_aliyun_sms(phone, template_code, params)
        # elif provider == 'tencent':
        #     await self._send_tencent_sms(phone, template_code, params)

    async def notify_appointment_success(self, appointment_id: str):
        """预约成功通知

        向患者发送预约成功的站内信通知。
        """
        appointment_result = await self.db.execute(
            select(Appointment)
            .options(selectinload(Appointment.schedule))
            .where(Appointment.id == appointment_id)
        )
        appointment = appointment_result.scalar_one_or_none()
        if not appointment:
            logger.warning(f"预约成功通知失败: 预约 {appointment_id} 不存在")
            return

        schedule = appointment.schedule
        time_slot_map = {'morning': '上午', 'afternoon': '下午', 'evening': '晚上'}
        time_slot_text = time_slot_map.get(schedule.time_slot, schedule.time_slot) if schedule else ""
        schedule_date_str = schedule.schedule_date.strftime('%Y年%m月%d日') if schedule and schedule.schedule_date else ""

        content = (
            f"您已成功预约{appointment.doctor_name or ''}医生，"
            f"就诊日期：{schedule_date_str} {time_slot_text}，"
            f"排队号：{appointment.queue_number}号。请按时到院签到。"
        )

        try:
            from app.modules.messages.service_messages import MessageService
            message_service = MessageService(self.db)
            await message_service.send_appointment_notification(
                user_id=appointment.user_id,
                user_type="patient",
                title="预约成功",
                content=content,
                appointment_id=appointment_id,
            )
            logger.info(f"预约成功通知已发送: appointment_id={appointment_id}")
        except Exception as exc:
            logger.warning(f"预约成功通知发送失败: appointment_id={appointment_id}, error={exc}")

    async def notify_appointment_remind(self, appointment_id: str):
        """就诊提醒通知

        在就诊前向患者发送提醒站内信。
        """
        appointment_result = await self.db.execute(
            select(Appointment)
            .options(selectinload(Appointment.schedule))
            .where(Appointment.id == appointment_id)
        )
        appointment = appointment_result.scalar_one_or_none()
        if not appointment:
            logger.warning(f"就诊提醒通知失败: 预约 {appointment_id} 不存在")
            return

        schedule = appointment.schedule
        time_slot_map = {'morning': '上午', 'afternoon': '下午', 'evening': '晚上'}
        time_slot_text = time_slot_map.get(schedule.time_slot, schedule.time_slot) if schedule else ""
        schedule_date_str = schedule.schedule_date.strftime('%Y年%m月%d日') if schedule and schedule.schedule_date else ""

        content = (
            f"温馨提示：您预约的{appointment.doctor_name or ''}医生，"
            f"就诊日期：{schedule_date_str} {time_slot_text}，"
            f"排队号：{appointment.queue_number}号。请准时到院签到就诊。"
        )

        try:
            from app.modules.messages.service_messages import MessageService
            message_service = MessageService(self.db)
            await message_service.send_appointment_notification(
                user_id=appointment.user_id,
                user_type="patient",
                title="就诊提醒",
                content=content,
                appointment_id=appointment_id,
            )
            logger.info(f"就诊提醒通知已发送: appointment_id={appointment_id}")
        except Exception as exc:
            logger.warning(f"就诊提醒通知发送失败: appointment_id={appointment_id}, error={exc}")

    async def notify_queue_call(self, appointment_id: str):
        """叫号通知

        当医生叫号时，向患者发送站内信通知，同时通过 WebSocket 推送给医生端。
        """
        appointment_result = await self.db.execute(
            select(Appointment)
            .options(selectinload(Appointment.schedule))
            .where(Appointment.id == appointment_id)
        )
        appointment = appointment_result.scalar_one_or_none()
        if not appointment:
            logger.warning(f"叫号通知失败: 预约 {appointment_id} 不存在")
            return

        # 站内信通知患者
        content = (
            f"轮到您就诊了！{appointment.doctor_name or ''}医生正在呼叫您，"
            f"排队号：{appointment.queue_number}号，请及时前往诊室。"
        )

        try:
            from app.modules.messages.service_messages import MessageService
            message_service = MessageService(self.db)
            await message_service.send_appointment_notification(
                user_id=appointment.user_id,
                user_type="patient",
                title="叫号通知",
                content=content,
                appointment_id=appointment_id,
            )
            logger.info(f"叫号通知已发送: appointment_id={appointment_id}")
        except Exception as exc:
            logger.warning(f"叫号站内信通知发送失败: appointment_id={appointment_id}, error={exc}")
