"""统一响应格式中间件"""
import gzip
import json
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# 不需要包装响应的路径（OpenAPI 文档相关）
EXCLUDED_PATHS = {
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/openapi.json",
}


class UnifiedResponseMiddleware(BaseHTTPMiddleware):
    """统一响应格式中间件
    
    将所有接口的返回数据统一包装为:
    {
        "code": 200,
        "message": "success",
        "data": ...
    }
    
    注意：OpenAPI 文档相关路径会被排除，不做包装处理。
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 排除 OpenAPI 文档相关路径
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)
        
        response = await call_next(request)
        
        # 只处理 JSON 响应
        if response.headers.get("content-type", "").startswith("application/json"):
            # 读取原始响应体
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            try:
                # GZipMiddleware 可能已压缩响应体，需先解压
                if body[:2] == b'\x1f\x8b':
                    body = gzip.decompress(body)
                data = json.loads(body.decode())
                
                # 如果已经是统一格式，直接返回
                if isinstance(data, dict) and "code" in data and "message" in data:
                    return JSONResponse(
                        content=data,
                        status_code=response.status_code
                    )
                
                # 包装为统一格式
                # 2xx 状态码都是成功，不仅仅是 200
                is_success = 200 <= response.status_code < 300
                wrapped_data = {
                    "code": response.status_code,
                    "message": "success" if is_success else "error",
                    "data": data
                }
                
                return JSONResponse(
                    content=wrapped_data,
                    status_code=response.status_code
                )
            except json.JSONDecodeError:
                # 如果不是 JSON，直接返回原响应
                return Response(
                    content=body,
                    status_code=response.status_code,
                    media_type=response.media_type
                )
        
        return response

