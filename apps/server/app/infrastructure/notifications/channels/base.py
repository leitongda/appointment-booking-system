"""通知渠道基类"""
import logging
from abc import ABC, abstractmethod
from typing import Optional

from app.schemas.notification import NotificationEvent, NotificationContent


logger = logging.getLogger(__name__)


class BaseNotificationChannel(ABC):
    """通知渠道基类

    所有通知渠道适配器必须继承此类并实现 send 方法。
    """

    def __init__(self, db):
        self.db = db

    @abstractmethod
    async def send(self, event: NotificationEvent, content: NotificationContent) -> bool:
        """发送通知

        Args:
            event: 通知事件
            content: 渲染后的通知内容

        Returns:
            是否发送成功
        """
        pass

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """渠道名称（不依赖 db，可在注册时获取）"""
        pass

    async def validate_recipient(self, event: NotificationEvent) -> tuple[bool, Optional[str]]:
        """验证接收人信息是否完整

        Args:
            event: 通知事件

        Returns:
            (是否有效, 错误信息)
        """
        return True, None
