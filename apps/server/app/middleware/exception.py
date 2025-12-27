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
    """业务异常"""
    
    def __init__(self, message: str, code: int = 400):
        self.message = message
        self.code = code
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
    status_code: int = None
) -> JSONResponse:
    """创建统一的错误响应"""
    return JSONResponse(
        status_code=status_code or code,
        content={
            "code": code,
            "message": message,
            "data": data
        }
    )


async def business_exception_handler(request: Request, exc: BusinessError):
    """业务异常处理"""
    logger.warning(f"业务异常: {exc.message}, path={request.url.path}")
    return create_error_response(exc.code, exc.message)


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
    """HTTP 异常处理"""
    logger.warning(f"HTTP异常: {exc.detail}, status={exc.status_code}, path={request.url.path}")
    return create_error_response(
        exc.status_code,
        exc.detail if isinstance(exc.detail, str) else "请求错误，请检查后重试",
        status_code=exc.status_code
    )


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
        return create_error_response(400, "数据已存在或违反约束条件，请检查后重试")
    
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

