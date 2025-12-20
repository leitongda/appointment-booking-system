"""
API 限流中间件
基于 Redis 实现，支持多种限流策略
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, Callable
import time
import logging

from app.core.redis import get_redis

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    全局限流中间件
    
    支持：
    1. 全局限流：所有请求共享限制
    2. IP 限流：按 IP 地址限制
    3. 用户限流：按用户 ID 限制（需要认证）
    """
    
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
    
    async def dispatch(self, request: Request, call_next: Callable):
        if not self.enabled:
            return await call_next(request)
        
        # OPTIONS 预检请求不限流（CORS preflight）
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # 获取客户端 IP
        client_ip = self._get_client_ip(request)
        
        # 白名单路径（不限流）
        whitelist_paths = ["/health", "/docs", "/redoc", "/openapi.json"]
        if request.url.path in whitelist_paths:
            return await call_next(request)
        
        # 检查限流
        try:
            is_allowed, retry_after = await self._check_rate_limit(client_ip)
            if not is_allowed:
                logger.warning(f"请求被限流: IP={client_ip}, path={request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "code": 429,
                        "message": "请求过于频繁，请稍后再试",
                        "data": {"retry_after": retry_after}
                    },
                    headers={"Retry-After": str(retry_after)}
                )
        except Exception as e:
            # Redis 不可用时不影响正常请求
            logger.error(f"限流检查失败: {e}")
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实 IP"""
        # 优先从代理头获取
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def _check_rate_limit(self, client_ip: str) -> tuple[bool, int]:
        """
        检查是否超过限流
        
        使用滑动窗口算法
        
        Returns:
            (是否允许, 需要等待的秒数)
        """
        redis = await get_redis()
        now = int(time.time())
        
        # 每秒限流检查
        second_key = f"ratelimit:{client_ip}:second:{now}"
        second_count = await redis.incr(second_key)
        if second_count == 1:
            await redis.expire(second_key, 2)  # 2 秒过期
        
        if second_count > self.requests_per_second:
            return False, 1
        
        # 每分钟限流检查
        minute = now // 60
        minute_key = f"ratelimit:{client_ip}:minute:{minute}"
        minute_count = await redis.incr(minute_key)
        if minute_count == 1:
            await redis.expire(minute_key, 120)  # 2 分钟过期
        
        if minute_count > self.requests_per_minute:
            retry_after = 60 - (now % 60)
            return False, retry_after
        
        return True, 0


class EndpointRateLimiter:
    """
    接口级别限流装饰器
    
    用法:
    ```
    rate_limiter = EndpointRateLimiter()
    
    @router.post("/send-code")
    @rate_limiter.limit("5/minute")
    async def send_code(...):
        pass
    ```
    """
    
    def __init__(self):
        self._limits = {}
    
    def limit(self, rule: str):
        """
        限流规则
        
        Args:
            rule: 限流规则，格式为 "次数/时间单位"
                  例如: "5/minute", "100/hour", "10/second"
        """
        def decorator(func: Callable):
            async def wrapper(request: Request, *args, **kwargs):
                # 解析规则
                count, period = self._parse_rule(rule)
                
                # 获取客户端标识
                client_id = self._get_client_id(request)
                endpoint = f"{request.method}:{request.url.path}"
                
                # 检查限流
                is_allowed, retry_after = await self._check_limit(
                    client_id, endpoint, count, period
                )
                
                if not is_allowed:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"请求过于频繁，请 {retry_after} 秒后重试"
                    )
                
                return await func(request, *args, **kwargs)
            
            # 保持原函数的元信息
            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return wrapper
        
        return decorator
    
    def _parse_rule(self, rule: str) -> tuple[int, int]:
        """解析限流规则"""
        parts = rule.split("/")
        count = int(parts[0])
        
        period_map = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400
        }
        
        period_name = parts[1].lower()
        period = period_map.get(period_name, 60)
        
        return count, period
    
    def _get_client_id(self, request: Request) -> str:
        """获取客户端标识"""
        # 优先使用用户 ID
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"
        
        # 否则使用 IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        return f"ip:{request.client.host if request.client else 'unknown'}"
    
    async def _check_limit(
        self,
        client_id: str,
        endpoint: str,
        max_requests: int,
        period: int
    ) -> tuple[bool, int]:
        """检查接口限流"""
        try:
            redis = await get_redis()
            now = int(time.time())
            window = now // period
            
            key = f"endpoint_limit:{endpoint}:{client_id}:{window}"
            count = await redis.incr(key)
            
            if count == 1:
                await redis.expire(key, period * 2)
            
            if count > max_requests:
                retry_after = period - (now % period)
                return False, retry_after
            
            return True, 0
        except Exception as e:
            logger.error(f"接口限流检查失败: {e}")
            return True, 0  # Redis 不可用时放行


# 全局限流器实例
endpoint_limiter = EndpointRateLimiter()

