from app.modules.messages.service_messages import MessageService as modular_message_service
from app.modules.messages.service_templates import (
    MessageTemplateService as modular_message_template_service,
)
from app.services.message_service import (
    MessageService as legacy_message_service,
    MessageTemplateService as legacy_message_template_service,
)


def test_message_service_wrapper_reuses_modular_service():
    assert legacy_message_service is modular_message_service


def test_message_template_service_wrapper_reuses_modular_service():
    assert legacy_message_template_service is modular_message_template_service
