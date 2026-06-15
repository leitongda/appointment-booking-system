"""
Structured error response schemas.

Defines the contract between the FastAPI server and frontend clients.
All error responses follow the ErrorResponse envelope for consistent parsing.
"""
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _to_camel(string: str) -> str:
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class ErrorDetail(BaseModel):
    """Structured error detail with machine-readable code."""
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    code: str = Field(
        ...,
        description="Machine-readable error code, e.g. SCHEDULE_CONFLICT, QUOTA_EXCEEDED",
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
    )
    details: dict[str, Any] | None = Field(
        None,
        description="Additional error context (conflicts, field errors, etc.)",
    )


class ErrorResponse(BaseModel):
    """Standard API error response envelope.

    All error responses from the server follow this structure:
    {
        "code": 400,
        "message": "Human-readable message",
        "error": {
            "code": "SCHEDULE_CONFLICT",
            "message": "Detailed message",
            "details": { ... }
        }
    }

    When error_code is not set (legacy behavior), the `error` field is omitted:
    {
        "code": 400,
        "message": "Human-readable message"
    }
    """
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    code: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Error message")
    error: ErrorDetail | None = Field(
        None,
        description="Structured error detail (absent in legacy responses)",
    )
