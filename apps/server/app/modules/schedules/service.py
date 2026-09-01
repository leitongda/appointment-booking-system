"""Composed schedule service."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.schedules.service_batch_lifecycle import (
    ScheduleMutationBatchLifecycleMixin,
)
from app.modules.schedules.service_create import ScheduleMutationCreateMixin
from app.modules.schedules.service_delete import ScheduleMutationDeleteMixin
from app.modules.schedules.service_generation import ScheduleGenerationMixin
from app.modules.schedules.service_publish import ScheduleMutationPublishMixin
from app.modules.schedules.service_query import ScheduleQueryMixin
from app.modules.schedules.service_update import ScheduleMutationUpdateMixin


class ScheduleService(
    ScheduleQueryMixin,
    ScheduleMutationCreateMixin,
    ScheduleMutationUpdateMixin,
    ScheduleMutationBatchLifecycleMixin,
    ScheduleMutationPublishMixin,
    ScheduleMutationDeleteMixin,
    ScheduleGenerationMixin,
):
    def __init__(self, db: AsyncSession):
        self.db = db
