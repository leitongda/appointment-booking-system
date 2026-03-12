"""通知服务 - 兼容层

实际实现已迁移至 app.infrastructure.notification
"""
from app.infrastructure.notification.service import NotificationService

__all__ = ["NotificationService"]
