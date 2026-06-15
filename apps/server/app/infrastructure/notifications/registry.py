"""通知渠道注册表"""
import logging

from app.infrastructure.notifications.channels.base import BaseNotificationChannel

logger = logging.getLogger(__name__)


class ChannelRegistry:
    """通知渠道注册表

    管理可用渠道实例，支持按租户启用/禁用渠道。
    """

    def __init__(self):
        self._channels: dict[str, type[BaseNotificationChannel]] = {}

    def register(self, channel_class: type[BaseNotificationChannel]) -> None:
        """注册渠道类"""
        # 实例化一个临时对象获取 channel_name
        # 传入 None 作为 db，因为 channel_name 是 @property 不需要 db
        try:
            temp_instance = channel_class(None)
            channel_name = temp_instance.channel_name
        except Exception:
            # 如果无法获取 channel_name，使用类名
            channel_name = channel_class.__name__.lower().replace("channel", "")

        self._channels[channel_name] = channel_class
        logger.info(f"[渠道注册表] 注册渠道: {channel_name}")

    def get(self, channel_name: str) -> type[BaseNotificationChannel] | None:
        """获取渠道类"""
        return self._channels.get(channel_name)

    def list_channels(self) -> list[str]:
        """列出所有已注册渠道"""
        return list(self._channels.keys())

    def is_available(self, channel_name: str) -> bool:
        """检查渠道是否可用"""
        return channel_name in self._channels


# 全局渠道注册表实例
channel_registry = ChannelRegistry()


def register_channels():
    """注册所有内置渠道"""
    from app.infrastructure.notifications.channels.email import EmailChannel
    from app.infrastructure.notifications.channels.in_app import InAppChannel
    from app.infrastructure.notifications.channels.sms import SmsChannel
    from app.infrastructure.notifications.channels.websocket import WebSocketChannel
    from app.infrastructure.notifications.channels.wechat import WechatChannel

    channel_registry.register(InAppChannel)
    channel_registry.register(WechatChannel)
    channel_registry.register(SmsChannel)
    channel_registry.register(EmailChannel)
    channel_registry.register(WebSocketChannel)
