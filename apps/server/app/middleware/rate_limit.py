"""
API 限流中间件
基于 Redis 滑动窗口实现,按租户+IP 维度隔离限流
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, Callable, List
import time
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    全局限流中间件

    限流维度：租户 + 客户端 IP + 请求路径
    不同租户的流量互不影响，一个租户高流量不会触发其他租户的限流。

    策略：
    1. 每秒限制: 同一租户+IP+路径，每秒最多 N 次请求
    2. 每分钟限制: 同一租户+IP+路径，每分钟最多 M 次请求
    """

    # 不参与限流的路径前缀
    EXCLUDE_PATHS = ["/health", "/docs", "/redoc", "/openapi.json"]

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_second: int = 10,
        enabled: bool = True
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_second = requests_per_second
        self.enabled = enabled
        self._redis = None
        self._get_redis_func = None

    async def _get_redis(self):
        """延迟获取 Redis 客户端"""
        if self._redis is None:
            from app.core.redis import get_redis as _get_redis_impl
            self._redis = await _get_redis_impl()
        return self._redis

    def _build_rate_limit_key(
        self,
        tenant_id: Optional[str],
        client_ip: str,
        path: str,
        window: str,
    ) -> str:
        """构建按租户隔离的限流键

        键格式: rate_limit:{tenant_id}:{client_ip}:{path}:{window}
        tenant_id 为 None 时使用 "global" 作为占位符，
        确保无租户上下文的请求也受限于同一个桶，不会与有租户的请求混淆。

        Args:
            tenant_id: 当前租户 ID（可能为 None）
            client_ip: 客户端 IP 地址
            path: 请求路径
            window: 时间窗口标识（"sec" 或 "min"）
        """
        tenant_part = tenant_id if tenant_id else "global"
        return f"rate_limit:{tenant_part}:{client_ip}:{path}:{window}"

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实 IP，支持反向代理场景"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        # 连接断开时 client 可能为 None
        if request.client:
            return request.client.host
        return "unknown"

    async def _check_rate_limit(self, key: str, limit: int, window_seconds: int) -> bool:
        """基于 Redis 滑动窗口检查是否超过限流阈值

        使用 ZSET 存储请求时间戳，清理过期记录后判断数量。

        Returns:
            True 表示允许通过，False 表示超过限流
        """
        try:
            redis = await self._get_redis()
            now = time.time()
            window_start = now - window_seconds

            pipeline = redis.pipeline()
            # 移除窗口外的旧记录
            pipeline.zremrangebyscore(key, 0, window_start)
            # 统计窗口内请求数
            pipeline.zcard(key)
            # 添加当前请求时间戳
            pipeline.zadd(key, {str(now): now})
            # 设置 key 过期时间，避免内存泄漏
            pipeline.expire(key, window_seconds + 1)
            results = await pipeline.execute()

            current_count = results[1]
            return current_count < limit
        except Exception as e:
            # Redis 异常时放行，避免因限流组件故障导致所有请求被拒
            logger.error(f"限流检查异常 (key={key}): {e}")
            return True

    async def dispatch(self, request: Request, call_next: Callable):
        """限流中间件主逻辑"""
        # 未启用时直接放行
        if not self.enabled:
            return await call_next(request)

        # 跳过不需要限流的路径
        path = request.url.path
        for exclude_path in self.EXCLUDE_PATHS:
            if path.startswith(exclude_path):
                return await call_next(request)

        # 获取当前租户 ID（可能为 None，如平台管理员或公开接口）
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        client_ip = self._get_client_ip(request)

        # 按租户隔离的每秒限流
        sec_key = self._build_rate_limit_key(tenant_id, client_ip, path, "sec")
        if not await self._check_rate_limit(sec_key, self.requests_per_second, window_seconds=1):
            logger.warning(
                f"每秒限流触发: tenant={tenant_id}, ip={client_ip}, path={path}"
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "code": 429,
                    "message": "请求过于频繁，请稍后再试",
                    "data": None,
                },
                headers={"Retry-After": "1"},
            )

        # 按租户隔离的每分钟限流
        min_key = self._build_rate_limit_key(tenant_id, client_ip, path, "min")
        if not await self._check_rate_limit(min_key, self.requests_per_minute, window_seconds=60):
            logger.warning(
                f"每分钟限流触发: tenant={tenant_id}, ip={client_ip}, path={path}"
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "code": 429,
                    "message": "请求过于频繁，请稍后再试",
                    "data": None,
                },
                headers={"Retry-After": "60"},
            )

        return await call_next(request)
