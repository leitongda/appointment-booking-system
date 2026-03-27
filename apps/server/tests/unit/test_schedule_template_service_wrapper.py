from app.modules.schedule_templates.service import (
    ScheduleTemplateService as modular_schedule_template_service,
)
from app.modules.schedule_templates.service import (
    ScheduleTemplateService as legacy_schedule_template_service,
)


def test_schedule_template_service_wrapper_reuses_modular_service():
    assert legacy_schedule_template_service is modular_schedule_template_service
