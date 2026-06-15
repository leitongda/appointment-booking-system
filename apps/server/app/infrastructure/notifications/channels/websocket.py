"""WebSocket 渠道适配器"""
import logging
from datetime import datetime

from app.core.websocket import WSMessageType, notify_doctor
from app.infrastructure.notifications.channels.base import BaseNotificationChannel
from app.models.notification_log import NotificationLog
from app.schemas.notification import NotificationContent, NotificationEvent

logger = logging.getLogger(__name__)


class WebSocketChannel(BaseNotificationChannel):
    """WebSocket 渠道

    通过 WebSocket 向医生端推送实时通知。
    """

    # 消息类型映射
    MESSAGE_TYPE_MAP = {
        "appointment": WSMessageType.NEW_APPOINTMENT,
        "schedule": WSMessageType.SCHEDULE_SUSPENDED,
        "stop_clinic": WSMessageType.SCHEDULE_SUSPENDED,
        "system": WSMessageType.SYSTEM_MESSAGE,
        "queue_call": WSMessageType.PATIENT_CALLED,
    }

    @property
    def channel_name(self) -> str:
        return "websocket"

    async def validate_recipient(self, event: NotificationEvent) -> tuple[bool, str | None]:
        """WebSocket 只支持医生类型"""
        if event.recipient_type != "doctor":
            return False, "WebSocket 仅支持医生用户"
        return True, None

    async def send(self, event: NotificationEvent, content: NotificationContent) -> bool:
        """发送 WebSocket 通知"""
        try:
            # 映射消息类型
            ws_message_type = self.MESSAGE_TYPE_MAP.get(
                event.message_type,
                WSMessageType.SYSTEM_MESSAGE
            )

            # 构建消息数据
            message_data = {
                "title": content.title,
                "content": content.content,
                "message_type": event.message_type,
                "related_id": event.related_id,
            }

            # 发送通知
            await notify_doctor(event.recipient_id, ws_message_type, message_data)

            # 记录通知日志
            dispatch_meta = (event.extra_data or {}).get("_dispatch", {})
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
                recipient=f"doctor:{event.recipient_id}",
                related_id=event.related_id,
                sent_at=datetime.utcnow(),
                primary_channel=dispatch_meta.get("primary_channel"),
                fallback_reason=dispatch_meta.get("fallback_reason"),
                channel_attempt_order=dispatch_meta.get("channel_attempt_order"),
            )
            self.db.add(log)

            logger.info(f"[WebSocket] 发送成功: doctor={event.recipient_id}, type={event.message_type}")
            return True

        except Exception as e:
            logger.error(f"[WebSocket] 发送失败: {e}", exc_info=True)

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
                    recipient=f"doctor:{event.recipient_id}",
                    related_id=event.related_id,
                    error_message=str(e),
                )
                self.db.add(log)
            except Exception:
                pass

            return False
