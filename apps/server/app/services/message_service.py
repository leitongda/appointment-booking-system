"""Message service compatibility exports."""

from app.modules.messages.service_messages import MessageService
from app.modules.messages.service_templates import MessageTemplateService

__all__ = ["MessageService", "MessageTemplateService"]
