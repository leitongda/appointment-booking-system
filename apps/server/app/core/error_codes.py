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
    SCHEDULE_STOPPED = "SCHEDULE_STOPPED"
    SAME_DAY_BOOKING_DISABLED = "SAME_DAY_BOOKING_DISABLED"
    BOOKING_LIMIT_EXCEEDED = "BOOKING_LIMIT_EXCEEDED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"

    # ── Appointment errors ───────────────────────────────────────────
    APPOINTMENT_NOT_FOUND = "APPOINTMENT_NOT_FOUND"
    APPOINTMENT_ALREADY_CANCELLED = "APPOINTMENT_ALREADY_CANCELLED"
    APPOINTMENT_INVALID_STATUS = "APPOINTMENT_INVALID_STATUS"
    DUPLICATE_BOOKING = "DUPLICATE_BOOKING"
    ADVANCE_BOOKING_EXCEEDED = "ADVANCE_BOOKING_EXCEEDED"
    REST_DAY_BOOKING = "REST_DAY_BOOKING"
    DOCTOR_APPOINTMENT_LIMIT_EXCEEDED = "DOCTOR_APPOINTMENT_LIMIT_EXCEEDED"
    CANCEL_WINDOW_NOT_OPENED = "CANCEL_WINDOW_NOT_OPENED"
    CANCEL_WINDOW_CLOSED = "CANCEL_WINDOW_CLOSED"
    CHECKIN_NOT_OPENED = "CHECKIN_NOT_OPENED"
    CHECKIN_WINDOW_CLOSED = "CHECKIN_WINDOW_CLOSED"
    CHECKIN_LIMIT_EXCEEDED = "CHECKIN_LIMIT_EXCEEDED"
    SCHEDULE_TENANT_MISMATCH = "SCHEDULE_TENANT_MISMATCH"
    USER_TENANT_MISMATCH = "USER_TENANT_MISMATCH"
    PATIENT_TENANT_MISMATCH = "PATIENT_TENANT_MISMATCH"

    # ── Patient errors ───────────────────────────────────────────────
    PATIENT_NOT_FOUND = "PATIENT_NOT_FOUND"
    PATIENT_BLACKLISTED = "PATIENT_BLACKLISTED"

    # ── Waitlist errors ──────────────────────────────────────────────
    WAITLIST_FULL = "WAITLIST_FULL"
    WAITLIST_DUPLICATE = "WAITLIST_DUPLICATE"

    # ── Payment errors ───────────────────────────────────────────────
    PAYMENT_REQUIRED = "PAYMENT_REQUIRED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    REFUND_EXCEEDED = "REFUND_EXCEEDED"

    # ── Tenant / subscription errors ─────────────────────────────────
    TENANT_DISABLED = "TENANT_DISABLED"
    TENANT_OVERDUE = "TENANT_OVERDUE"
    TENANT_TRIAL_EXPIRED = "TENANT_TRIAL_EXPIRED"
    TENANT_SUSPENDED_WRITE = "TENANT_SUSPENDED_WRITE"

    # ── General / auth errors ────────────────────────────────────────
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RATE_LIMITED = "RATE_LIMITED"
    TENANT_SUSPENDED = "TENANT_SUSPENDED"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"

    # ── Template / platform errors ───────────────────────────────────
    TEMPLATE_NOT_FOUND = "TEMPLATE_NOT_FOUND"
    TENANT_NAME_EXISTS = "TENANT_NAME_EXISTS"

    # ── Infrastructure errors ────────────────────────────────────────
    LOCK_ACQUISITION_FAILED = "LOCK_ACQUISITION_FAILED"
