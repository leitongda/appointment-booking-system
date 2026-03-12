"""Compatibility exports for shared response models."""

from app.schemas.response import COMMON_RESPONSES, ErrorResponse, PageResponse, Response, ResponseModel, ValidationErrorResponse

__all__ = [
    "COMMON_RESPONSES",
    "ErrorResponse",
    "PageResponse",
    "Response",
    "ResponseModel",
    "ValidationErrorResponse",
]
