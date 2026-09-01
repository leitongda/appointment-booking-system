"""Backward-compat thin re-export.

Historically this module held the monolithic ``ScheduleMutationMixin``. The
implementation has been split (verbatim method bodies) into focused mixins:

- :mod:`service_create`  -> :class:`ScheduleMutationCreateMixin`
- :mod:`service_update`  -> :class:`ScheduleMutationUpdateMixin`
- :mod:`service_batch_lifecycle` -> :class:`ScheduleMutationBatchLifecycleMixin`
- :mod:`service_publish` -> :class:`ScheduleMutationPublishMixin`
- :mod:`service_delete`  -> :class:`ScheduleMutationDeleteMixin`

:class:`ScheduleMutationMixin` is preserved as an aggregate re-export so that
existing ``from app.modules.schedules.service_mutation import ScheduleMutationMixin``
imports keep working. The composed :class:`~app.modules.schedules.service.ScheduleService`
now wires the five focused mixins directly.
"""

from app.modules.schedules.service_batch_lifecycle import (
    ScheduleMutationBatchLifecycleMixin,
)
from app.modules.schedules.service_create import ScheduleMutationCreateMixin
from app.modules.schedules.service_delete import ScheduleMutationDeleteMixin
from app.modules.schedules.service_publish import ScheduleMutationPublishMixin
from app.modules.schedules.service_update import ScheduleMutationUpdateMixin

__all__ = ["ScheduleMutationMixin"]


class ScheduleMutationMixin(
    ScheduleMutationCreateMixin,
    ScheduleMutationUpdateMixin,
    ScheduleMutationBatchLifecycleMixin,
    ScheduleMutationPublishMixin,
    ScheduleMutationDeleteMixin,
):
    """Aggregate mutation mixin kept for backward-compat imports only."""
