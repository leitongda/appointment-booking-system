"""
全局异常处理中间件
统一处理各类异常，返回标准格式的错误响应
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from jose import JWTError
import logging
import traceback

logger = logging.getLogger(__name__)


class BusinessError(Exception):
    """业务异常

    Args:
        message: Human-readable error message.
        code: HTTP status code (default 400).
        error_code: Machine-readable error code (e.g. "SCHEDULE_CONFLICT").
            When set, the error response includes a structured ``error`` envelope.
        details: Optional dict with extra context (conflicts, field errors, etc.).
    """

    def __init__(
        self,
        message: str,
        code: int = 400,
        error_code: str | None = None,
        details: dict | None = None,
    ):
        self.message = message
        self.code = code
        self.error_code = error_code
        self.details = details
        super().__init__(message)


class AuthenticationError(Exception):
    """认证异常"""
    
    def __init__(self, message: str = "身份验证失败，请重新登录"):
        self.message = message
        super().__init__(message)


class PermissionDeniedError(Exception):
    """权限不足异常"""
    
    def __init__(self, message: str = "权限不足，请联系管理员"):
        self.message = message
        super().__init__(message)


class NotFoundError(Exception):
    """资源不存在异常"""
    
    def __init__(self, message: str = "资源不存在，请检查后重试"):
        self.message = message
        super().__init__(message)


def create_error_response(
    code: int,
    message: str,
    data: any = None,
    status_code: int = None,
    error_code: str | None = None,
    error_details: dict | None = None,
) -> JSONResponse:
    """创建统一的错误响应

    When *error_code* is provided, the response includes a structured ``error``
    envelope that the frontend can use for branching logic::

        {
            "code": 400,
            "message": "...",
            "error": {
                "code": "SCHEDULE_CONFLICT",
                "message": "...",
                "details": { ... }
            }
        }

    When *error_code* is ``None`` (legacy behaviour), the ``error`` key is
    omitted and the response keeps the old shape::

        {"code": 400, "message": "...", "data": ...}
    """
    content: dict = {
        "code": code,
        "message": message,
    }
    if error_code is not None:
        error_block: dict = {"code": error_code, "message": message}
        if error_details is not None:
            error_block["details"] = error_details
        content["error"] = error_block
    elif data is not None:
        # Legacy path: only include data when no structured error_code
        content["data"] = data

    return JSONResponse(
        status_code=status_code or code,
        content=content,
    )


async def business_exception_handler(request: Request, exc: BusinessError):
    """业务异常处理

    When the BusinessError carries an *error_code*, the response includes the
    structured ``error`` envelope.  Otherwise the legacy flat format is used.
    """
    logger.warning(f"业务异常: {exc.message}, error_code={exc.error_code}, path={request.url.path}")
    return create_error_response(
        exc.code,
        exc.message,
        error_code=exc.error_code,
        error_details=exc.details,
    )


async def authentication_exception_handler(request: Request, exc: AuthenticationError):
    """认证异常处理"""
    logger.warning(f"认证失败: {exc.message}, path={request.url.path}")
    return create_error_response(401, exc.message, status_code=status.HTTP_401_UNAUTHORIZED)


async def permission_exception_handler(request: Request, exc: PermissionDeniedError):
    """权限异常处理"""
    logger.warning(f"权限不足: {exc.message}, path={request.url.path}")
    return create_error_response(403, exc.message, status_code=status.HTTP_403_FORBIDDEN)


async def not_found_exception_handler(request: Request, exc: NotFoundError):
    """资源不存在处理"""
    logger.warning(f"资源不存在: {exc.message}, path={request.url.path}")
    return create_error_response(404, exc.message, status_code=status.HTTP_404_NOT_FOUND)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP 异常处理

    detail 为 dict 时，若包含 ``error_code`` 则输出结构化 ``error`` 信封：
        raise HTTPException(403, detail={
            "error_code": "TENANT_OVERDUE",
            "message": "租户已欠费，请续费后继续使用",
        })
    →  ``{"code": 403, "message": "...", "error": {"code": "TENANT_OVERDUE", "message": "..."}}``

    detail 为字符串时回落到原行为。
    """
    logger.warning(f"HTTP异常: {exc.detail}, status={exc.status_code}, path={request.url.path}")
    if isinstance(exc.detail, dict):
        msg = exc.detail.get("message") or "请求错误，请检查后重试"
        err_code = exc.detail.get("error_code")
        err_details = exc.detail.get("data") or exc.detail.get("details")
        return create_error_response(
            code=exc.status_code,
            message=msg,
            status_code=exc.status_code,
            error_code=err_code,
            error_details=err_details if isinstance(err_details, dict) else None,
        )
    return create_error_response(
        exc.status_code,
        exc.detail if isinstance(exc.detail, str) else "请求错误，请检查后重试",
        status_code=exc.status_code,
    )


def raise_business_http_error(
    status_code: int,
    error_code: str,
    message: str,
    data: any = None,
    details: dict | None = None,
) -> None:
    """抛出带结构化 error_code 的 HTTPException

    供登录/鉴权依赖等需要前端按 code 分支的场景使用。
    The exception handler will wrap *error_code* into the ``error`` envelope.
    """
    from fastapi import HTTPException

    detail: dict = {"error_code": error_code, "message": message}
    if data is not None:
        detail["data"] = data
    if details is not None:
        detail["details"] = details
    raise HTTPException(status_code=status_code, detail=detail)


def _sanitize_error(error: dict) -> dict:
    """清理错误信息，确保可以 JSON 序列化"""
    sanitized = {}
    for key, value in error.items():
        if isinstance(value, bytes):
            # 将 bytes 转换为字符串
            try:
                sanitized[key] = value.decode('utf-8', errors='replace')
            except Exception:
                sanitized[key] = str(value)
        elif isinstance(value, (list, tuple)):
            sanitized[key] = [
                v.decode('utf-8', errors='replace') if isinstance(v, bytes) else str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
                for v in value
            ]
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_error(value)
        elif not isinstance(value, (str, int, float, bool, type(None), list, dict)):
            sanitized[key] = str(value)
        else:
            sanitized[key] = value
    return sanitized


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求参数验证异常处理"""
    errors = exc.errors()
    
    # 提取友好的错误信息
    error_messages = []
    for error in errors:
        loc = " -> ".join(str(l) for l in error.get("loc", []))
        msg = error.get("msg", "参数错误")
        error_messages.append(f"{loc}: {msg}")
    
    message = "请求参数错误，请检查后重试"
    if error_messages:
        message = error_messages[0]  # 返回第一个错误
    
    logger.warning(f"参数验证失败: {error_messages}, path={request.url.path}")
    
    # 清理错误信息，确保可以 JSON 序列化
    sanitized_errors = [_sanitize_error(e) for e in errors]
    
    return create_error_response(
        422,
        message,
        data={"errors": sanitized_errors},
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )


async def jwt_exception_handler(request: Request, exc: JWTError):
    """JWT 异常处理"""
    logger.warning(f"JWT异常: {str(exc)}, path={request.url.path}")
    return create_error_response(401, "身份验证失败，请重新登录", status_code=status.HTTP_401_UNAUTHORIZED)


async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """数据库异常处理"""
    logger.error(f"数据库异常: {str(exc)}, path={request.url.path}")
    logger.error(traceback.format_exc())
    
    # 处理唯一约束冲突
    if isinstance(exc, IntegrityError):
        error_str = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
        
        # 尝试提取更详细的错误信息
        error_message = "数据已存在或违反约束条件，请检查后重试"
        
        # 检查是否是外键约束错误
        if "foreign key" in error_str.lower() or "violates foreign key constraint" in error_str.lower():
            if "store_id" in error_str:
                error_message = "门店不存在，请检查门店ID"
            elif "doctor_id" in error_str:
                error_message = "医生不存在，请检查医生ID"
            elif "department_id" in error_str:
                error_message = "科室不存在，请检查科室ID"
            else:
                error_message = "关联数据不存在，请检查后重试"
        # 检查是否是唯一约束错误
        elif "unique constraint" in error_str.lower() or "duplicate key" in error_str.lower():
            error_message = "数据已存在，请勿重复创建"
        # 检查是否是 NOT NULL 约束错误
        elif "not null" in error_str.lower() or "null value" in error_str.lower():
            error_message = "必填字段不能为空，请检查后重试"
        
        return create_error_response(400, error_message)
    
    return create_error_response(500, "操作失败，请稍后重试", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理（兜底）"""
    logger.error(f"未处理的异常: {type(exc).__name__}: {str(exc)}, path={request.url.path}")
    logger.error(traceback.format_exc())
    
    # 生产环境不暴露详细错误信息
    return create_error_response(
        500,
        "服务器异常，请稍后重试",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def register_exception_handlers(app):
    """注册所有异常处理器"""
    app.add_exception_handler(BusinessError, business_exception_handler)
    app.add_exception_handler(AuthenticationError, authentication_exception_handler)
    app.add_exception_handler(PermissionDeniedError, permission_exception_handler)
    app.add_exception_handler(NotFoundError, not_found_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(JWTError, jwt_exception_handler)
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)

