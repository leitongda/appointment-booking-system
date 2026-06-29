"""
API 限流中间件
基于 Redis 滑动窗口实现,按租户+IP 维度隔离限流

支持按租户差异化限流:
- Tenant.rate_limit_per_minute / rate_limit_per_second 可覆盖全局默认值
- 租户限流配置缓存在 Redis (key: tenant_rate_limit:{tenant_id})，TTL 5 分钟
- 缓存未命中时回退到全局默认值（不在中间件中查 DB）
"""
import logging
import time
from collections.abc import Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Redis 缓存 key 前缀 + TTL
_TENANT_LIMIT_CACHE_PREFIX = "tenant_rate_limit:"
_TENANT_LIMIT_CACHE_TTL = 300  # 5 分钟


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
    # 完全跳过限流的路径（高频埋点上报，由路由自身的 IP 限流兜底）
    EXCLUDE_EXACT_PATHS = (
        "/api/v1/analytics/track",
        "/api/v1/analytics/batch",
        # rrweb 会话录制批量上报：前端 100 条/30s 一批，多用户并发会撞 rpm=300 全局限流，
        # 与 analytics/batch 一致由路由内 IP 限流兜底。
        "/api/v1/session-events/batch",
    )

    def __init__(
        self,
        app,
        requests_per_minute: int = 300,
        requests_per_second: int = 50,
        enabled: bool = True
    ):
        super().__init__(app)
        self.default_rpm = requests_per_minute
        self.default_rps = requests_per_second
        self.enabled = enabled
        self._redis = None
        self._get_redis_func = None

    async def _get_redis(self):
        """延迟获取 Redis 客户端"""
        if self._redis is None:
            from app.core.redis import get_redis as _get_redis_impl
            self._redis = await _get_redis_impl()
        return self._redis

    async def _get_tenant_limits(self, tenant_id: str) -> tuple[int, int]:
        """从 Redis 缓存获取租户专属限流配置

        Returns:
            (requests_per_minute, requests_per_second)
            缓存未命中时回退到全局默认值。
        """
        try:
            redis = await self._get_redis()
            cache_key = f"{_TENANT_LIMIT_CACHE_PREFIX}{tenant_id}"
            cached = await redis.get(cache_key)
            if cached:
                import json
                data = json.loads(cached)
                rpm = data.get("rpm", self.default_rpm)
                rps = data.get("rps", self.default_rps)
                return rpm, rps
        except Exception:
            pass
        return self.default_rpm, self.default_rps

    @staticmethod
    async def cache_tenant_limits(
        tenant_id: str,
        rate_limit_per_minute: int | None,
        rate_limit_per_second: int | None,
        default_rpm: int = 300,
        default_rps: int = 50,
    ):
        """将租户限流配置写入 Redis 缓存（供外部调用，如租户更新接口）"""
        try:
            from app.core.redis import get_redis as _get_redis_impl
            redis = await _get_redis_impl()
            cache_key = f"{_TENANT_LIMIT_CACHE_PREFIX}{tenant_id}"
            import json
            data = json.dumps({
                "rpm": rate_limit_per_minute if rate_limit_per_minute is not None else default_rpm,
                "rps": rate_limit_per_second if rate_limit_per_second is not None else default_rps,
            })
            await redis.setex(cache_key, _TENANT_LIMIT_CACHE_TTL, data)
        except Exception as e:
            logger.error(f"缓存租户限流配置失败 (tenant={tenant_id}): {e}")

    @staticmethod
    async def invalidate_tenant_limits(tenant_id: str):
        """清除租户限流缓存（供外部调用，如租户删除）"""
        try:
            from app.core.redis import get_redis as _get_redis_impl
            redis = await _get_redis_impl()
            cache_key = f"{_TENANT_LIMIT_CACHE_PREFIX}{tenant_id}"
            await redis.delete(cache_key)
        except Exception as e:
            logger.error(f"清除租户限流缓存失败 (tenant={tenant_id}): {e}")

    def _build_rate_limit_key(
        self,
        tenant_id: str | None,
        client_ip: str,
        path: str,
        window: str,
    ) -> str:
        """构建按租户隔离的限流键"""
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
        if request.client:
            return request.client.host
        return "unknown"

    async def _check_rate_limit(self, key: str, limit: int, window_seconds: int) -> bool:
        """基于 Redis 滑动窗口检查是否超过限流阈值"""
        try:
            redis = await self._get_redis()
            now = time.time()
            window_start = now - window_seconds

            pipeline = redis.pipeline()
            pipeline.zremrangebyscore(key, 0, window_start)
            pipeline.zcard(key)
            pipeline.zadd(key, {str(now): now})
            pipeline.expire(key, window_seconds + 1)
            results = await pipeline.execute()

            current_count = results[1]
            return current_count < limit
        except Exception as e:
            logger.error(f"限流检查异常 (key={key}): {e}")
            return True

    @staticmethod
    async def check_ip_rate_limit(
        redis,
        client_ip: str,
        scope: str,
        limit: int,
        window_seconds: int = 60,
    ) -> bool:
        """基于 Redis 滑动窗口的通用 IP 限流检查（供路由层复用）。

        与中间件自身的 _check_rate_limit 同构，区别在于：
        - 调用方自行获取 redis 客户端（避免路由层依赖中间件实例）
        - 限流 key 形如 rate_limit:ip:{scope}:{ip}:{window}，独立于中间件维度

        多实例部署下，所有 worker 共享同一个 Redis，限流全局生效——
        这是路由层从"进程内内存 dict"迁移到 Redis 的核心收益。

        Args:
            redis: redis.asyncio 客户端实例
            client_ip: 客户端 IP
            scope: 限流作用域（如 "session_events_batch"，避免不同接口互相干扰）
            limit: 窗口内最大请求数
            window_seconds: 窗口大小（秒），默认 60

        Returns:
            True 表示允许通过，False 表示超限
        """
        try:
            now = time.time()
            window_start = now - window_seconds
            key = f"rate_limit:ip:{scope}:{client_ip}:{window_seconds}"

            pipeline = redis.pipeline()
            pipeline.zremrangebyscore(key, 0, window_start)
            pipeline.zcard(key)
            pipeline.zadd(key, {str(now): now})
            pipeline.expire(key, window_seconds + 1)
            results = await pipeline.execute()

            current_count = results[1]
            return current_count < limit
        except Exception as e:
            # Redis 异常时放行（fail-open），避免限流基础设施抖动阻断正常请求
            logger.error(f"路由级限流检查异常 (scope={scope}, ip={client_ip}): {e}")
            return True

    async def dispatch(self, request: Request, call_next: Callable):
        """限流中间件主逻辑"""
        if not self.enabled:
            return await call_next(request)

        path = request.url.path
        for exclude_path in self.EXCLUDE_PATHS:
            if path.startswith(exclude_path):
                return await call_next(request)

        # 高频埋点接口完全跳过全局限流（由路由自身 IP 限流兜底）
        if path in self.EXCLUDE_EXACT_PATHS:
            return await call_next(request)

        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        # 获取租户专属限流配置（或回退全局默认值）
        rpm, rps = self.default_rpm, self.default_rps
        if tenant_id:
            rpm, rps = await self._get_tenant_limits(tenant_id)

        client_ip = self._get_client_ip(request)

        # 每秒限流
        sec_key = self._build_rate_limit_key(tenant_id, client_ip, path, "sec")
        if not await self._check_rate_limit(sec_key, rps, window_seconds=1):
            logger.warning(f"每秒限流触发: tenant={tenant_id}, ip={client_ip}, path={path}, limit={rps}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"code": 429, "message": "请求过于频繁，请稍后再试", "data": None},
                headers={"Retry-After": "1"},
            )

        # 每分钟限流
        min_key = self._build_rate_limit_key(tenant_id, client_ip, path, "min")
        if not await self._check_rate_limit(min_key, rpm, window_seconds=60):
            logger.warning(f"每分钟限流触发: tenant={tenant_id}, ip={client_ip}, path={path}, limit={rpm}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"code": 429, "message": "请求过于频繁，请稍后再试", "data": None},
                headers={"Retry-After": "60"},
            )

        return await call_next(request)
