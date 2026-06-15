"""
安全响应头中间件

在所有 HTTP 响应中注入安全相关的 Header，防止常见的 Web 攻击：
- X-Content-Type-Options: 防止 MIME 类型嗅探
- X-Frame-Options: 防止点击劫持
- Strict-Transport-Security: 强制 HTTPS（仅生产环境）
- X-XSS-Protection: 浏览器 XSS 过滤
- Referrer-Policy: 控制 Referer 泄露
- Permissions-Policy: 限制浏览器 API 权限
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """为所有 HTTP 响应添加安全相关的 Header"""

    def __init__(self, app, hsts_enabled: bool = False):
        super().__init__(app)
        self.hsts_enabled = hsts_enabled

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )

        # HSTS 仅在非 DEBUG 且显式启用时添加
        if self.hsts_enabled:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response
