"""
Prometheus 指标中间件

采集 HTTP 请求指标，供 Prometheus 抓取：
- http_requests_total: 请求计数（按 method, path, status_code, tenant_id）
- http_request_duration_seconds: 请求耗时直方图（按 method, path）
- http_requests_in_flight: 当前正在处理的请求数
"""
import time
import logging
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from app.middleware.tenant_context import get_current_tenant_id

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 指标定义
# ---------------------------------------------------------------------------

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code", "tenant_id"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

http_requests_in_flight = Gauge(
    "http_requests_in_flight",
    "Number of HTTP requests currently being processed",
)


def _normalise_path(path: str) -> str:
    """将动态路径段替换为占位符，避免高基数标签。

    /api/v1/users/123/appointments/456  ->  /api/v1/users/{id}/appointments/{id}
    """
    segments = path.split("/")
    normalised: list[str] = []
    for seg in segments:
        # 纯数字 ID 或 UUID 视为动态段
        if seg.isdigit() or (len(seg) == 36 and seg.count("-") == 4):
            normalised.append("{id}")
        else:
            normalised.append(seg)
    return "/".join(normalised)


# ---------------------------------------------------------------------------
# 中间件
# ---------------------------------------------------------------------------

class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """采集 HTTP 指标并暴露给 Prometheus。"""

    EXCLUDE_PATHS = frozenset({"/metrics", "/health", "/health/detailed"})

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # 跳过 metrics 自身和健康检查，避免递归与噪音
        if path in self.EXCLUDE_PATHS:
            return await call_next(request)

        normalised = _normalise_path(path)
        method = request.method

        http_requests_in_flight.inc()
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            # 5xx 由全局异常处理器处理，这里只确保指标正确
            duration = time.perf_counter() - start
            http_request_duration_seconds.labels(method=method, path=normalised).observe(duration)
            http_requests_total.labels(
                method=method,
                path=normalised,
                status_code="500",
                tenant_id=get_current_tenant_id() or "",
            ).inc()
            raise
        finally:
            http_requests_in_flight.dec()

        duration = time.perf_counter() - start
        status_code = str(response.status_code)
        tenant_id = get_current_tenant_id() or ""

        http_request_duration_seconds.labels(method=method, path=normalised).observe(duration)
        http_requests_total.labels(
            method=method,
            path=normalised,
            status_code=status_code,
            tenant_id=tenant_id,
        ).inc()

        return response


# ---------------------------------------------------------------------------
# /metrics 端点响应体
# ---------------------------------------------------------------------------

def get_metrics_response() -> Response:
    """返回 Prometheus 格式的指标数据。"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
