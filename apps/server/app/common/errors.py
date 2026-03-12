"""Common server error types."""


class AppError(Exception):
    """Base application error with an optional stable error code."""

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code


class PermissionDeniedError(AppError):
    """Raised when the current actor does not have enough permissions."""


class ResourceNotFoundError(AppError):
    """Raised when the requested resource does not exist."""


class ValidationFailedError(AppError):
    """Raised when domain validation fails."""
