"""Primary appointment service entrypoint."""

from app.core.events import dispatch_event_email
from app.core.redis import RedisCache
from app.modules.appointments.common import APPOINTMENT_STATUS
from app.modules.appointments.service_booking import AppointmentBookingService
from app.modules.appointments.service_flow import AppointmentFlowService
from app.services.message_service import MessageService
from app.services.rule_engine_service import RuleEngineService
from app.services.settings_service import SettingsService


class AppointmentService(AppointmentBookingService, AppointmentFlowService):
    """Composed appointment service."""

    pass


__all__ = [
    "APPOINTMENT_STATUS",
    "AppointmentService",
    "RedisCache",
    "RuleEngineService",
    "MessageService",
    "SettingsService",
    "dispatch_event_email",
]
