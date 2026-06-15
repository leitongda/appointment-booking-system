"""统一通知基础设施"""
from .dispatcher import NotificationDispatcher
from .registry import channel_registry, register_channels

__all__ = [
    "NotificationDispatcher",
    "channel_registry",
    "register_channels",
]
