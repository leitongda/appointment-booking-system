"""微信服务 - 兼容层

实际实现已迁移至 app.infrastructure.wechat
"""
from app.infrastructure.wechat.token_manager import WechatTokenManager
from app.infrastructure.wechat.service import WechatService

__all__ = ["WechatTokenManager", "WechatService"]
