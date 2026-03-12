"""Composed schedule template service."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.schedule_templates.service_generation import ScheduleTemplateGenerationMixin
from app.modules.schedule_templates.service_mutation import ScheduleTemplateMutationMixin
from app.modules.schedule_templates.service_query import ScheduleTemplateQueryMixin


class ScheduleTemplateService(
    ScheduleTemplateQueryMixin,
    ScheduleTemplateMutationMixin,
    ScheduleTemplateGenerationMixin,
):
    def __init__(self, db: AsyncSession):
        self.db = db
