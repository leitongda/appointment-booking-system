"""微信订阅消息渠道适配器"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.notification import NotificationEvent, NotificationContent
from app.models.notification_log import NotificationLog
from app.models.user import User
from app.infrastructure.notifications.channels.base import BaseNotificationChannel
from app.infrastructure.wechat.service import WechatService
from datetime import datetime


logger = logging.getLogger(__name__)


class WechatChannel(BaseNotificationChannel):
    """微信订阅消息渠道

    通过 WechatService 发送微信小程序订阅消息。
    """

    @property
    def channel_name(self) -> str:
        return "wechat"

    async def validate_recipient(self, event: NotificationEvent) -> tuple[bool, str | None]:
        """微信需要 openid"""
        if not event.recipient_openid:
            # 尝试从数据库获取 openid
            if event.recipient_type == "patient":
                result = await self.db.execute(
                    select(User.openid).where(User.id == event.recipient_id)
                )
                openid = await result.scalar_one_or_none()
                if not openid:
                    return False, "用户未绑定微信或缺少 openid"
                event.recipient_openid = openid
            else:
                return False, "缺少微信 openid"
        return True, None

    async def send(self, event: NotificationEvent, content: NotificationContent) -> bool:
        """发送微信订阅消息"""
        try:
            # 检查是否有微信模板配置
            template_id = await self._get_template_id(event.template_code, event.tenant_id)
            if not template_id:
                logger.warning(f"[微信] 未配置模板: {event.template_code}，跳过发送")
                return False

            # 构建模板数据
            template_data = self._build_template_data(content, event.variables)

            # 发送订阅消息
            wechat_service = WechatService(self.db, store_id=event.store_id)
            success = await wechat_service.send_subscribe_message(
                openid=event.recipient_openid,
                template_id=template_id,
                data=template_data,
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
                    recipient=event.recipient_openid,
                    related_id=event.related_id,
                    sent_at=datetime.utcnow(),
                )
                self.db.add(log)

                logger.info(f"[微信] 发送成功: user={event.recipient_id}, template={event.template_code}")
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
                    recipient=event.recipient_openid,
                    related_id=event.related_id,
                    error_message="微信接口返回失败",
                )
                self.db.add(log)

            return success

        except Exception as e:
            logger.error(f"[微信] 发送失败: {e}", exc_info=True)

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
                    recipient=event.recipient_openid or "",
                    related_id=event.related_id,
                    error_message=str(e),
                )
                self.db.add(log)
            except Exception:
                pass

            return False

    async def _get_template_id(self, template_code: str, tenant_id: str) -> str | None:
        """获取微信模板 ID

        TODO: 从 system_settings 或专门的模板配置表读取
        """
        # 临时实现：返回 None 表示未配置
        return None

    def _build_template_data(self, content: NotificationContent, variables: dict) -> dict:
        """构建微信模板数据

        微信订阅消息格式：
        {
            "thing1": {"value": "预约成功"},
            "thing2": {"value": "李医生"},
            "date3": {"value": "2024-01-01 09:00"}
        }
        """
        # 临时实现：直接使用 variables
        # 实际应该根据模板配置映射字段
        return {k: {"value": str(v)} for k, v in variables.items()}
