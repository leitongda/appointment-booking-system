"""站内信渠道适配器"""
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.notification import NotificationEvent, NotificationContent
from app.schemas.message import MessageCreate, MessageType
from app.models.message import Message
from app.models.notification_log import NotificationLog
from app.infrastructure.notifications.channels.base import BaseNotificationChannel
from app.utils.audit import set_create_audit


logger = logging.getLogger(__name__)


class InAppChannel(BaseNotificationChannel):
    """站内信渠道

    包装现有的 MessageService，将通知创建为站内信。
    """

    @property
    def channel_name(self) -> str:
        return "in_app"

    async def validate_recipient(self, event: NotificationEvent) -> tuple[bool, str | None]:
        """站内信只需要用户ID"""
        if not event.recipient_id:
            return False, "缺少接收用户ID"
        if not event.recipient_type:
            return False, "缺少接收用户类型"
        return True, None

    async def send(self, event: NotificationEvent, content: NotificationContent) -> bool:
        """发送站内信"""
        try:
            # 映射消息类型
            message_type = self._map_message_type(event.message_type)

            # 创建消息
            message = Message(
                id=str(__import__("uuid").uuid4()),
                tenant_id=event.tenant_id,
                store_id=event.store_id,
                user_id=event.recipient_id,
                user_type=event.recipient_type,
                title=content.title,
                content=content.content,
                message_type=message_type,
                related_id=event.related_id,
            )
            set_create_audit(message)
            self.db.add(message)
            await self.db.flush()

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
                recipient=f"{event.recipient_type}:{event.recipient_id}",
                related_id=event.related_id,
                sent_at=datetime.utcnow(),
            )
            self.db.add(log)

            logger.info(
                f"[站内信] 发送成功: user={event.recipient_id}, type={event.message_type}, title={content.title}"
            )
            return True

        except Exception as e:
            logger.error(f"[站内信] 发送失败: {e}", exc_info=True)
            return False

    def _map_message_type(self, message_type: str) -> str:
        """映射消息类型到 Message 模型的类型"""
        type_map = {
            "appointment": "appointment",
            "appointment_success": "appointment",
            "appointment_reminder": "schedule",
            "appointment_cancelled": "appointment",
            "schedule": "schedule",
            "stop_clinic": "stop_clinic",
            "system": "system",
            "consultation": "consultation",
            "feedback": "feedback",
            "queue_call": "appointment",
        }
        return type_map.get(message_type, "system")
