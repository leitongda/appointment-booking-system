"""统一响应格式中间件"""
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import json
from typing import Callable


class UnifiedResponseMiddleware(BaseHTTPMiddleware):
    """统一响应格式中间件
    
    将所有接口的返回数据统一包装为:
    {
        "code": 200,
        "message": "success",
        "data": ...
    }
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # 只处理 JSON 响应
        if response.headers.get("content-type", "").startswith("application/json"):
            # 读取原始响应体
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            try:
                data = json.loads(body.decode())
                
                # 如果已经是统一格式，直接返回
                if isinstance(data, dict) and "code" in data and "message" in data:
                    return JSONResponse(
                        content=data,
                        status_code=response.status_code
                    )
                
                # 包装为统一格式
                wrapped_data = {
                    "code": response.status_code,
                    "message": "success" if response.status_code == 200 else "error",
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

