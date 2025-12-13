from typing import TypeVar, Generic, Optional, List
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
    data: Optional[T] = None


class PageResponse(BaseModel, Generic[T]):
    """分页响应格式"""
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        by_alias=True,  # 序列化时使用 camelCase
    )
    
    code: int = 200
    message: str = "success"
    data: Optional[List[T]] = None
    total: int = 0
    page: int = 1
    page_size: int = Field(default=10, alias="pageSize")


# 别名，兼容旧代码
ResponseModel = Response

