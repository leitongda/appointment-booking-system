"""
请求日志中间件
记录每个请求的详细信息，包括耗时、状态码、trace_id 等结构化字段
"""
import logging
import time
import uuid
from collections.abc import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.middleware.tenant_context import get_current_tenant_id
from app.utils.ip import get_client_ip

logger = logging.getLogger("request")


class RequestLogMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json", "/metrics"]

    async def dispatch(self, request: Request, call_next: Callable):
        # 跳过不需要记录的路径
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # 生成请求 ID（作为 trace_id 用于跨服务追踪）
        trace_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        request.state.request_id = trace_id

        # 获取客户端 IP
        client_ip = self._get_client_ip(request)

        # 记录开始时间
        start_time = time.time()

        # 请求信息
        method = request.method
        path = request.url.path
        query = str(request.query_params) if request.query_params else ""
        tenant_id = get_current_tenant_id()

        # 结构化日志：请求入口
        logger.info(
            "request_started",
            extra={
                "trace_id": trace_id,
                "tenant_id": tenant_id or "",
                "user_id": "",
                "method": method,
                "path": path,
                "query": query,
                "client_ip": client_ip,
                "duration_ms": 0,
            },
        )

        # 处理请求
        try:
            response = await call_next(request)

            # 计算耗时
            duration_ms = (time.time() - start_time) * 1000

            # 尝试从 request.state 获取 user_id（路由处理器可能已设置）
            user_id = getattr(getattr(request, "state", None), "user_id", "") or ""

            # 记录响应
            status_code = response.status_code
            log_func = logger.info if status_code < 400 else logger.warning
            log_func(
                "request_completed",
                extra={
                    "trace_id": trace_id,
                    "tenant_id": tenant_id or "",
                    "user_id": user_id,
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2),
                    "client_ip": client_ip,
                },
            )

            # 添加响应头
            response.headers["X-Request-ID"] = trace_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            user_id = getattr(getattr(request, "state", None), "user_id", "") or ""
            logger.error(
                "request_error",
                extra={
                    "trace_id": trace_id,
                    "tenant_id": tenant_id or "",
                    "user_id": user_id,
                    "method": method,
                    "path": path,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "duration_ms": round(duration_ms, 2),
                    "client_ip": client_ip,
                },
            )
            raise

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实 IP（使用统一的工具函数）"""
        return get_client_ip(request)

