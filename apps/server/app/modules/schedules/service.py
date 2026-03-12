"""Composed schedule service."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.schedules.service_generation import ScheduleGenerationMixin
from app.modules.schedules.service_mutation import ScheduleMutationMixin
from app.modules.schedules.service_query import ScheduleQueryMixin


class ScheduleService(
    ScheduleQueryMixin,
    ScheduleMutationMixin,
    ScheduleGenerationMixin,
):
    def __init__(self, db: AsyncSession):
        self.db = db
