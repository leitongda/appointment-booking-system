"""租户并发会话限制

通过 Redis 有序集合维护租户维度的活跃会话，
支持限制同一租户同时在线的管理员数量。
"""
import time
import logging

logger = logging.getLogger(__name__)


class SessionLimiter:
    """租户并发会话限制器"""

    KEY_PREFIX = "session_limiter"

    @classmethod
    def _key(cls, tenant_id: str) -> str:
        return f"{cls.KEY_PREFIX}:{tenant_id}"

    @classmethod
    async def register_session(
        cls,
        tenant_id: str,
        admin_id: str,
        session_token_hash: str,
        ttl_seconds: int = 86400,
    ) -> dict:
        """注册一个新会话

        Returns:
            {"allowed": bool, "current_count": int, "max_allowed": int}
        """
        max_sessions = 10
        try:
            from app.common.quota import QuotaChecker
            from app.db.session import async_session_maker

            async with async_session_maker() as db:
                checker = QuotaChecker(db)
                quota = await checker.get_quota_usage(tenant_id)
                admin_quota = quota.get("admins", {})
                max_sessions = admin_quota.get("limit", 10)
        except Exception:
            pass

        from app.core.redis import RedisCache
        redis = RedisCache.get_client()
        key = cls._key(tenant_id)
        now = time.time()
        member = f"{admin_id}:{session_token_hash}"

        pipe = redis.pipeline()
        pipe.zadd(key, {member: now})
        pipe.zremrangebyscore(key, "-inf", now - ttl_seconds)
        pipe.zcard(key)
        results = await pipe.execute()
        current_count = results[2]

        if current_count > max_sessions:
            await redis.zrem(key, member)
            return {
                "allowed": False,
                "current_count": current_count - 1,
                "max_allowed": max_sessions,
            }

        await redis.expire(key, ttl_seconds)
        return {
            "allowed": True,
            "current_count": current_count,
            "max_allowed": max_sessions,
        }

    @classmethod
    async def remove_session(cls, tenant_id: str, admin_id: str, session_token_hash: str) -> None:
        """移除一个会话（登出时调用）"""
        from app.core.redis import RedisCache
        redis = RedisCache.get_client()
        key = cls._key(tenant_id)
        member = f"{admin_id}:{session_token_hash}"
        await redis.zrem(key, member)

    @classmethod
    async def heartbeat(cls, tenant_id: str, admin_id: str, session_token_hash: str) -> None:
        """更新会话活跃时间"""
        from app.core.redis import RedisCache
        redis = RedisCache.get_client()
        key = cls._key(tenant_id)
        member = f"{admin_id}:{session_token_hash}"
        now = time.time()
        await redis.zadd(key, {member: now})
        await redis.expire(key, 86400)

    @classmethod
    async def get_active_count(cls, tenant_id: str) -> int:
        """获取当前活跃会话数"""
        from app.core.redis import RedisCache
        redis = RedisCache.get_client()
        key = cls._key(tenant_id)
        now = time.time()
        await redis.zremrangebyscore(key, "-inf", now - 86400)
        return await redis.zcard(key)
