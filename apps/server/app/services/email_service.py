"""邮件发送服务 - 兼容层

实际实现已迁移至 app.infrastructure.email
"""
from app.infrastructure.email.service import EmailService

__all__ = ["EmailService"]
