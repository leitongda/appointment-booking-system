"""
API 废弃端点检测中间件

当请求匹配已废弃的端点时，在响应中添加标准废弃头信息：
- Deprecation: true
- Sunset: <日期>
- X-API-Deprecated-Version: <废弃的 API 版本>
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeprecatedEndpoint:
    """废弃端点配置

    Attributes:
        path_prefix: 请求路径前缀（如 ``/api/v1/auth``）
        sunset_date: Sunset 日期，ISO 8601 格式（如 ``2025-12-31``）
        deprecated_version: 已废弃的 API 版本（如 ``v1``）
        replacement: 可选的替代路径提示
    """

    path_prefix: str
    sunset_date: str
    deprecated_version: str = "v1"
    replacement: str | None = None


class DeprecationMiddleware(BaseHTTPMiddleware):
    """废弃端点检测中间件

    检查请求路径是否匹配配置的废弃端点列表，若匹配则在响应头中添加
    标准废弃信息（RFC 8594 Sunset Header）。

    Args:
        deprecated_endpoints: 废弃端点配置列表
    """

    def __init__(
        self,
        app,
        deprecated_endpoints: list[DeprecatedEndpoint] | None = None,
    ):
        super().__init__(app)
        self._endpoints = deprecated_endpoints or []

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        for endpoint in self._endpoints:
            if request.url.path.startswith(endpoint.path_prefix):
                self._add_deprecation_headers(response, endpoint)
                break

        return response

    def _add_deprecation_headers(
        self, response: Response, endpoint: DeprecatedEndpoint
    ) -> None:
        """向响应添加废弃头信息"""
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = endpoint.sunset_date
        response.headers["X-API-Deprecated-Version"] = endpoint.deprecated_version

        if endpoint.replacement:
            response.headers["X-API-Replacement"] = endpoint.replacement

        logger.info(
            "废弃端点被访问: path=%s, sunset=%s, version=%s",
            endpoint.path_prefix,
            endpoint.sunset_date,
            endpoint.deprecated_version,
        )
