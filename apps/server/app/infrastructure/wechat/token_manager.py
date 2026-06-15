"""微信 Token 管理器

支持 access_token 的 Redis 缓存和分布式锁机制（多租户隔离）
"""
import logging

import httpx

from app.core.redis import RedisCache, SyncRedisCache, cache, sync_cache
from app.middleware.tenant_context import get_current_tenant_id

logger = logging.getLogger(__name__)


class WechatTokenManager:
    """
    微信 Token 管理器

    特性：
    1. Redis 缓存：Token 缓存在 Redis 中，过期时间 7000 秒
    2. 分布式锁：防止多进程/多实例并发刷新 Token
    3. 双重检查：获取锁后再次检查缓存，避免重复刷新
    """

    WECHAT_API_URL = "https://api.weixin.qq.com"
    TOKEN_CACHE_EXPIRE = 7000  # Token 缓存时间（秒），微信 Token 有效期 7200 秒
    LOCK_TIMEOUT = 10  # 锁超时时间（秒）
    LOCK_RETRY_TIMES = 3  # 获取锁重试次数

    @classmethod
    async def get_access_token(
        cls,
        app_id: str,
        app_secret: str,
        force_refresh: bool = False,
        tenant_id: str | None = None,
    ) -> str:
        """
        获取微信 access_token（异步，带分布式锁，支持多租户隔离）

        Args:
            app_id: 小程序 AppID
            app_secret: 小程序 AppSecret
            force_refresh: 是否强制刷新
            tenant_id: 租户ID（可选，不传则从上下文获取）

        Returns:
            access_token

        Raises:
            ValueError: 获取 Token 失败
        """
        if not app_id or not app_secret:
            raise ValueError("微信配置不完整，缺少 AppID 或 AppSecret")

        effective_tenant_id = tenant_id or get_current_tenant_id()

        # 1. 如果不是强制刷新，先尝试从缓存获取
        if not force_refresh:
            cached_token = await cache.get_wechat_token(app_id, tenant_id=effective_tenant_id)
            if cached_token:
                logger.debug(f"[微信Token] 缓存命中: app_id={app_id}")
                return cached_token

        # 2. 缓存未命中或强制刷新，获取分布式锁
        lock_name = f"wechat:token:{app_id}"
        lock_value = await RedisCache.acquire_lock(
            lock_name,
            timeout=cls.LOCK_TIMEOUT,
            retry_times=cls.LOCK_RETRY_TIMES
        )

        if not lock_value:
            # 获取锁失败，等待一下再尝试从缓存获取（可能其他进程已刷新）
            import asyncio
            await asyncio.sleep(0.5)
            cached_token = await cache.get_wechat_token(app_id, tenant_id=effective_tenant_id)
            if cached_token:
                logger.info(f"[微信Token] 等待后缓存命中: app_id={app_id}")
                return cached_token
            raise ValueError("获取微信 Token 失败：无法获取分布式锁")

        try:
            # 3. 双重检查：获取锁后再次检查缓存（DCL 模式）
            if not force_refresh:
                cached_token = await cache.get_wechat_token(app_id, tenant_id=effective_tenant_id)
                if cached_token:
                    logger.info(f"[微信Token] DCL 缓存命中: app_id={app_id}")
                    return cached_token

            # 4. 调用微信 API 获取新 Token
            logger.info(f"[微信Token] 请求新 Token: app_id={app_id}")
            token = await cls._fetch_access_token_from_wechat(app_id, app_secret)

            # 5. 缓存新 Token
            await cache.set_wechat_token(app_id, token, cls.TOKEN_CACHE_EXPIRE, tenant_id=effective_tenant_id)
            logger.info(f"[微信Token] 已缓存新 Token: app_id={app_id}")

            return token

        finally:
            # 6. 释放锁
            await RedisCache.release_lock(lock_name, lock_value)

    @classmethod
    async def _fetch_access_token_from_wechat(cls, app_id: str, app_secret: str) -> str:
        """从微信 API 获取 access_token"""
        url = f"{cls.WECHAT_API_URL}/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": app_id,
            "secret": app_secret
        }

        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
            response = await client.get(url, params=params)
            data = response.json()

        if "errcode" in data and data["errcode"] != 0:
            error_msg = data.get('errmsg', '未知错误')
            error_code = data.get('errcode')
            logger.error(f"[微信Token] API 请求失败: errcode={error_code}, errmsg={error_msg}")
            raise ValueError(f"获取 access_token 失败: {error_msg}")

        token = data.get("access_token", "")
        if not token:
            raise ValueError("获取 access_token 失败: 返回数据中无 token")

        return token

    @classmethod
    def get_access_token_sync(
        cls,
        app_id: str,
        app_secret: str,
        force_refresh: bool = False,
        tenant_id: str | None = None,
    ) -> str:
        """
        获取微信 access_token（同步版本，用于 Celery 任务，支持多租户隔离）

        Args:
            app_id: 小程序 AppID
            app_secret: 小程序 AppSecret
            force_refresh: 是否强制刷新
            tenant_id: 租户ID（可选，Celery 任务中无上下文，需显式传入）

        Returns:
            access_token
        """
        import time

        if not app_id or not app_secret:
            raise ValueError("微信配置不完整")

        # 1. 尝试从缓存获取
        if not force_refresh:
            cached_token = sync_cache.get_wechat_token(app_id, tenant_id=tenant_id)
            if cached_token:
                logger.debug(f"[微信Token] 同步缓存命中: app_id={app_id}")
                return cached_token

        # 2. 获取分布式锁
        lock_name = f"wechat:token:{app_id}"
        lock_value = SyncRedisCache.acquire_lock(
            lock_name,
            timeout=cls.LOCK_TIMEOUT,
            retry_times=cls.LOCK_RETRY_TIMES
        )

        if not lock_value:
            time.sleep(0.5)
            cached_token = sync_cache.get_wechat_token(app_id, tenant_id=tenant_id)
            if cached_token:
                return cached_token
            raise ValueError("获取微信 Token 失败：无法获取分布式锁")

        try:
            # 3. 双重检查
            if not force_refresh:
                cached_token = sync_cache.get_wechat_token(app_id, tenant_id=tenant_id)
                if cached_token:
                    return cached_token

            # 4. 调用微信 API
            url = f"{cls.WECHAT_API_URL}/cgi-bin/token"
            params = {
                "grant_type": "client_credential",
                "appid": app_id,
                "secret": app_secret
            }

            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, params=params)
                data = response.json()

            if "errcode" in data and data["errcode"] != 0:
                raise ValueError(f"获取 access_token 失败: {data.get('errmsg')}")

            token = data.get("access_token", "")
            if not token:
                raise ValueError("获取 access_token 失败: 返回数据中无 token")

            # 5. 缓存新 Token
            sync_cache.set_wechat_token(app_id, token, cls.TOKEN_CACHE_EXPIRE, tenant_id=tenant_id)
            logger.info(f"[微信Token] 同步已缓存新 Token: app_id={app_id}")

            return token

        finally:
            SyncRedisCache.release_lock(lock_name, lock_value)
