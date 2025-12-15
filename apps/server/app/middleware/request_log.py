"""
请求日志中间件
记录每个请求的详细信息，包括耗时、状态码等
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
import logging
import uuid

logger = logging.getLogger("request")


class RequestLogMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable):
        # 跳过不需要记录的路径
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # 生成请求 ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        
        # 获取客户端 IP
        client_ip = self._get_client_ip(request)
        
        # 记录开始时间
        start_time = time.time()
        
        # 请求信息
        method = request.method
        path = request.url.path
        query = str(request.query_params) if request.query_params else ""
        
        logger.info(f"[{request_id}] --> {method} {path} {query} | IP: {client_ip}")
        
        # 处理请求
        try:
            response = await call_next(request)
            
            # 计算耗时
            duration_ms = (time.time() - start_time) * 1000
            
            # 记录响应
            status_code = response.status_code
            log_func = logger.info if status_code < 400 else logger.warning
            log_func(
                f"[{request_id}] <-- {method} {path} | "
                f"Status: {status_code} | "
                f"Duration: {duration_ms:.2f}ms"
            )
            
            # 添加响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"[{request_id}] <-- {method} {path} | "
                f"Error: {type(e).__name__}: {str(e)} | "
                f"Duration: {duration_ms:.2f}ms"
            )
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实 IP"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"

