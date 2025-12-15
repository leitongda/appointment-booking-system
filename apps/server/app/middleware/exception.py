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
    
    def __init__(self, message: str = "认证失败"):
        self.message = message
        super().__init__(message)


class PermissionDeniedError(Exception):
    """权限不足异常"""
    
    def __init__(self, message: str = "权限不足"):
        self.message = message
        super().__init__(message)


class NotFoundError(Exception):
    """资源不存在异常"""
    
    def __init__(self, message: str = "资源不存在"):
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
        exc.detail if isinstance(exc.detail, str) else "请求错误",
        status_code=exc.status_code
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求参数验证异常处理"""
    errors = exc.errors()
    
    # 提取友好的错误信息
    error_messages = []
    for error in errors:
        loc = " -> ".join(str(l) for l in error.get("loc", []))
        msg = error.get("msg", "参数错误")
        error_messages.append(f"{loc}: {msg}")
    
    message = "参数验证失败"
    if error_messages:
        message = error_messages[0]  # 返回第一个错误
    
    logger.warning(f"参数验证失败: {error_messages}, path={request.url.path}")
    
    return create_error_response(
        422,
        message,
        data={"errors": errors},
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )


async def jwt_exception_handler(request: Request, exc: JWTError):
    """JWT 异常处理"""
    logger.warning(f"JWT异常: {str(exc)}, path={request.url.path}")
    return create_error_response(401, "Token无效或已过期", status_code=status.HTTP_401_UNAUTHORIZED)


async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """数据库异常处理"""
    logger.error(f"数据库异常: {str(exc)}, path={request.url.path}")
    logger.error(traceback.format_exc())
    
    # 处理唯一约束冲突
    if isinstance(exc, IntegrityError):
        return create_error_response(400, "数据已存在或违反约束条件")
    
    return create_error_response(500, "数据库操作失败", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理（兜底）"""
    logger.error(f"未处理的异常: {type(exc).__name__}: {str(exc)}, path={request.url.path}")
    logger.error(traceback.format_exc())
    
    # 生产环境不暴露详细错误信息
    return create_error_response(
        500,
        "服务器内部错误",
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

