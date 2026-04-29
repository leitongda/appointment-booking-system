"""短信渠道适配器"""
import logging
from datetime import datetime

from app.schemas.notification import NotificationEvent, NotificationContent
from app.models.notification_log import NotificationLog
from app.infrastructure.notifications.channels.base import BaseNotificationChannel
from app.infrastructure.sms.service import SmsService


logger = logging.getLogger(__name__)


class SmsChannel(BaseNotificationChannel):
    """短信渠道

    通过 SmsService 发送业务短信通知。
    """

    # 短信消息类型映射
    MESSAGE_TYPE_MAP = {
        "appointment_success": "appointment_success",
        "appointment_reminder": "appointment_reminder",
        "appointment_cancelled": "appointment_cancelled",
        "stop_clinic": "stop_clinic",
    }

    @property
    def channel_name(self) -> str:
        return "sms"

    async def validate_recipient(self, event: NotificationEvent) -> tuple[bool, str | None]:
        """短信需要手机号"""
        if not event.recipient_phone:
            return False, "缺少接收人手机号"
        return True, None

    async def send(self, event: NotificationEvent, content: NotificationContent) -> bool:
        """发送短信"""
        try:
            # 映射到 SmsService 支持的消息类型
            sms_message_type = self.MESSAGE_TYPE_MAP.get(event.message_type)
            if not sms_message_type:
                logger.warning(f"[短信] 不支持的消息类型: {event.message_type}")
                return False

            # 构建模板变量
            template_variables = {k: str(v) for k, v in event.variables.items()}

            # 调用 SmsService 发送
            sms_method = getattr(SmsService, f"send_{sms_message_type}", None)
            if not sms_method:
                logger.warning(f"[短信] 未找到发送方法: {sms_message_type}")
                return False

            success = await sms_method(
                tenant_id=event.tenant_id,
                phone=event.recipient_phone,
                variables=template_variables,
                user_id=event.recipient_id,
                store_id=event.store_id,
                appointment_id=event.related_id,  # SmsService 使用 appointment_id 参数
            )

            if success:
                logger.info(f"[短信] 发送成功: user={event.recipient_id}, type={sms_message_type}")
            else:
                logger.warning(f"[短信] 发送失败: user={event.recipient_id}, type={sms_message_type}")

            return success

        except Exception as e:
            logger.error(f"[短信] 发送失败: {e}", exc_info=True)

            # 记录失败日志
            try:
                log = NotificationLog(
                    tenant_id=event.tenant_id,
                    store_id=event.store_id,
                    user_id=event.recipient_id,
                    user_type=event.recipient_type,
                    channel=self.channel_name,
                    message_type=event.message_type,
                    title=content.title,
                    status="failed",
                    recipient=event.recipient_phone or "",
                    related_id=event.related_id,
                    error_message=str(e),
                )
                self.db.add(log)
            except Exception:
                pass

            return False
