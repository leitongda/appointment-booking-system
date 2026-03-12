"""短信验证码服务 - 兼容层

实际实现已迁移至 app.infrastructure.sms
"""
from app.infrastructure.sms.service import SmsService

__all__ = ["SmsService"]
