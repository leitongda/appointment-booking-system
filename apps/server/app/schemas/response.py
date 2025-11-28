from typing import TypeVar, Generic, Optional, List
from pydantic import BaseModel

T = TypeVar('T')

class Response(BaseModel, Generic[T]):
    """统一响应格式"""
    code: int = 200
    message: str = "success"
    data: Optional[T] = None

class PageResponse(BaseModel, Generic[T]):
    """分页响应格式"""
    code: int = 200
    message: str = "success"
    data: Optional[List[T]] = None
    total: int = 0
    page: int = 1
    page_size: int = 10

# 别名，兼容旧代码
ResponseModel = Response

