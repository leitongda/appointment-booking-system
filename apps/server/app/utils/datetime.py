"""Timezone-aware datetime utilities."""
from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)
