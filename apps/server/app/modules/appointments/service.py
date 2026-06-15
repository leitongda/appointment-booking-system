"""Primary appointment service entrypoint."""

from app.core.events import dispatch_event_email
from app.core.redis import RedisCache
from app.modules.appointments.common import APPOINTMENT_STATUS
from app.modules.appointments.service_booking import AppointmentBookingService
from app.modules.appointments.service_flow import AppointmentFlowService
from app.modules.rule_engine import RuleEngineService
from app.modules.settings.service import SettingsService
from app.modules.unified_message.compat import MessageServiceCompat as MessageService


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
