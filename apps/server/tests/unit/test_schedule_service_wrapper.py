from app.modules.schedules.service import ScheduleService as modular_schedule_service
from app.services.schedule_service import ScheduleService as legacy_schedule_service


def test_schedule_service_wrapper_reuses_modular_service():
    assert legacy_schedule_service is modular_schedule_service
