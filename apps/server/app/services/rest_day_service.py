import warnings

warnings.warn(
    "app.services.rest_day_service is deprecated, "
    "use app.modules.rest_days.service instead.",
    DeprecationWarning,
    stacklevel=2,
)

from app.modules.rest_days.service import RestDayService  # noqa: E402, F401

__all__ = ["RestDayService"]
