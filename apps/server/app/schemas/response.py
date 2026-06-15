from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar('T')


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class Response(BaseModel, Generic[T]):
    """统一响应格式"""
    code: int = 200
    message: str = "success"
    data: T | None = None


class PageResponse(BaseModel, Generic[T]):
    """分页响应格式"""
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,  # 序列化时使用 camelCase
    )
    
    code: int = 200
    message: str = "success"
    data: list[T] | None = None
    total: int = 0
    page: int = 1
    page_size: int = Field(default=10, alias="pageSize")


# ==================== 错误响应模型（用于 OpenAPI 文档） ====================

class ErrorResponse(BaseModel):
    """错误响应格式
    
    用于 OpenAPI 文档中声明错误响应的结构
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": 400,
                "message": "请求参数错误",
                "detail": "schedule_id 不能为空"
            }
        }
    )
    
    code: int = Field(..., description="错误码", examples=[400, 401, 403, 404, 500])
    message: str = Field(..., description="错误消息", examples=["请求参数错误", "未认证", "无权限", "资源不存在"])
    detail: str | None = Field(None, description="详细错误信息")


class ValidationErrorResponse(BaseModel):
    """参数校验错误响应"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": 422,
                "message": "参数校验失败",
                "errors": [
                    {"field": "phone", "message": "手机号格式不正确"},
                    {"field": "password", "message": "密码长度至少6位"}
                ]
            }
        }
    )
    
    code: int = Field(422, description="错误码")
    message: str = Field("参数校验失败", description="错误消息")
    errors: list[dict] = Field(default_factory=list, description="字段级错误详情")


# ==================== 常用错误响应定义（用于 responses 参数） ====================

# 可以在路由装饰器中使用，例如：
# @router.get("/{id}", responses={**COMMON_RESPONSES})
COMMON_RESPONSES = {
    400: {
        "model": ErrorResponse,
        "description": "请求参数错误",
        "content": {
            "application/json": {
                "example": {"code": 400, "message": "请求参数错误", "detail": "参数格式不正确"}
            }
        }
    },
    401: {
        "model": ErrorResponse,
        "description": "未认证或 Token 过期",
        "content": {
            "application/json": {
                "example": {"code": 401, "message": "未认证", "detail": "Token 已过期，请重新登录"}
            }
        }
    },
    403: {
        "model": ErrorResponse,
        "description": "无权限访问",
        "content": {
            "application/json": {
                "example": {"code": 403, "message": "无权限", "detail": "您没有执行此操作的权限"}
            }
        }
    },
    404: {
        "model": ErrorResponse,
        "description": "资源不存在",
        "content": {
            "application/json": {
                "example": {"code": 404, "message": "资源不存在", "detail": "找不到指定的资源"}
            }
        }
    },
    422: {
        "model": ValidationErrorResponse,
        "description": "参数校验失败",
    },
    500: {
        "model": ErrorResponse,
        "description": "服务器内部错误",
        "content": {
            "application/json": {
                "example": {"code": 500, "message": "服务器错误", "detail": "请稍后重试"}
            }
        }
    },
}


# 别名，兼容旧代码
ResponseModel = Response

