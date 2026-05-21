"""
Machine-readable error codes for structured error responses.

These codes are part of the server-client contract. Frontend clients use them
to branch error handling logic (e.g. show conflict modal, redirect on permission
denied, throttle on rate limit).

Naming convention: SCREAMING_SNAKE_CASE, domain-prefixed.
"""


class ErrorCode:
    """Error code constants.

    Organized by domain. Each code maps to a specific client-side behavior.
    """

    # ── Schedule errors ──────────────────────────────────────────────
    SCHEDULE_CONFLICT = "SCHEDULE_CONFLICT"
    SCHEDULE_NOT_FOUND = "SCHEDULE_NOT_FOUND"
    SCHEDULE_ALREADY_SUSPENDED = "SCHEDULE_ALREADY_SUSPENDED"
    SCHEDULE_NOT_SUSPENDED = "SCHEDULE_NOT_SUSPENDED"
    SCHEDULE_HAS_APPOINTMENTS = "SCHEDULE_HAS_APPOINTMENTS"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"

    # ── Appointment errors ───────────────────────────────────────────
    APPOINTMENT_NOT_FOUND = "APPOINTMENT_NOT_FOUND"
    APPOINTMENT_ALREADY_CANCELLED = "APPOINTMENT_ALREADY_CANCELLED"

    # ── General / auth errors ────────────────────────────────────────
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RATE_LIMITED = "RATE_LIMITED"
    TENANT_SUSPENDED = "TENANT_SUSPENDED"
    TENANT_OVERDUE = "TENANT_OVERDUE"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
