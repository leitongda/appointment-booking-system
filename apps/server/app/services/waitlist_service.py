"""候补队列服务 - 兼容层

实际实现已迁移至 app.modules.waitlist.service
"""
from app.modules.waitlist.service import WaitlistService

__all__ = ["WaitlistService"]
