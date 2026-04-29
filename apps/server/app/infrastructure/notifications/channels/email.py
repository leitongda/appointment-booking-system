"""邮件渠道适配器"""
import logging
from datetime import datetime

from app.schemas.notification import NotificationEvent, NotificationContent
from app.models.notification_log import NotificationLog
from app.infrastructure.notifications.channels.base import BaseNotificationChannel
from app.infrastructure.email.service import EmailService


logger = logging.getLogger(__name__)


class EmailChannel(BaseNotificationChannel):
    """邮件渠道

    通过 EmailService 发送邮件通知。
    """

    @property
    def channel_name(self) -> str:
        return "email"

    async def validate_recipient(self, event: NotificationEvent) -> tuple[bool, str | None]:
        """邮件需要邮箱地址"""
        if not event.recipient_email:
            return False, "缺少接收人邮箱"
        return True, None

    async def send(self, event: NotificationEvent, content: NotificationContent) -> bool:
        """发送邮件"""
        try:
            email_service = EmailService(self.db)

            # 尝试使用模板发送
            success = await email_service.send_by_template(
                template_code=event.template_code,
                to_email=event.recipient_email,
                variables=event.variables,
            )

            if success:
                # 记录通知日志
                log = NotificationLog(
                    tenant_id=event.tenant_id,
                    store_id=event.store_id,
                    user_id=event.recipient_id,
                    user_type=event.recipient_type,
                    channel=self.channel_name,
                    message_type=event.message_type,
                    title=content.title,
                    content=content.content,
                    status="sent",
                    recipient=event.recipient_email,
                    related_id=event.related_id,
                    sent_at=datetime.utcnow(),
                )
                self.db.add(log)

                logger.info(f"[邮件] 发送成功: user={event.recipient_id}, email={event.recipient_email}")
            else:
                # 记录失败日志
                log = NotificationLog(
                    tenant_id=event.tenant_id,
                    store_id=event.store_id,
                    user_id=event.recipient_id,
                    user_type=event.recipient_type,
                    channel=self.channel_name,
                    message_type=event.message_type,
                    title=content.title,
                    status="failed",
                    recipient=event.recipient_email,
                    related_id=event.related_id,
                    error_message="邮件发送失败",
                )
                self.db.add(log)

            return success

        except Exception as e:
            logger.error(f"[邮件] 发送失败: {e}", exc_info=True)

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
                    recipient=event.recipient_email or "",
                    related_id=event.related_id,
                    error_message=str(e),
                )
                self.db.add(log)
            except Exception:
                pass

            return False
