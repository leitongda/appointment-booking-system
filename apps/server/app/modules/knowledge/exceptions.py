"""知识库领域异常：直接继承 HTTPException，detail 形状与 raise_business_http_error 一致

{"error_code": "...", "message": "..."}，前端据 error_code 做差异化提示。
"""
from fastapi import HTTPException, status


class KnowledgeError(HTTPException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    error_code: str = "KB_ERROR"

    def __init__(self, message: str, *, error_code: str | None = None, status_code: int | None = None):
        self.message = message
        super().__init__(
            status_code=status_code or self.status_code,
            detail={"error_code": error_code or self.error_code, "message": message},
        )


class KnowledgeNotFound(KnowledgeError):
    """不存在或不可见（跨租户、无任何权限）统一 404，不泄露资源是否存在"""
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "KB_NOT_FOUND"


class KnowledgeForbidden(KnowledgeError):
    """可见但权限级别不足"""
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "KB_FORBIDDEN"


class KnowledgeConflict(KnowledgeError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "KB_CONFLICT"


class KnowledgeInvalidFile(KnowledgeError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "KB_INVALID_FILE"


class KnowledgeEmbeddingMismatch(KnowledgeError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "KB_EMBEDDING_MISMATCH"


class KnowledgeEmbeddingUnavailable(KnowledgeError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "KB_EMBEDDING_UNAVAILABLE"
