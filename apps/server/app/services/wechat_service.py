"""
微信服务
提供微信小程序登录、获取手机号、发送订阅消息等功能
支持 access_token 的 Redis 缓存和分布式锁机制
"""
import httpx
from typing import Optional, Dict, Any
import logging

from app.services.settings_service import SettingsService
from app.core.redis import cache, RedisCache, sync_cache, SyncRedisCache
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession

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
        force_refresh: bool = False
    ) -> str:
        """
        获取微信 access_token（异步，带分布式锁）
        
        Args:
            app_id: 小程序 AppID
            app_secret: 小程序 AppSecret
            force_refresh: 是否强制刷新
            
        Returns:
            access_token
            
        Raises:
            ValueError: 获取 Token 失败
        """
        if not app_id or not app_secret:
            raise ValueError("微信配置不完整，缺少 AppID 或 AppSecret")
        
        # 1. 如果不是强制刷新，先尝试从缓存获取
        if not force_refresh:
            cached_token = await cache.get_wechat_token(app_id)
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
            cached_token = await cache.get_wechat_token(app_id)
            if cached_token:
                logger.info(f"[微信Token] 等待后缓存命中: app_id={app_id}")
                return cached_token
            raise ValueError("获取微信 Token 失败：无法获取分布式锁")
        
        try:
            # 3. 双重检查：获取锁后再次检查缓存（DCL 模式）
            if not force_refresh:
                cached_token = await cache.get_wechat_token(app_id)
                if cached_token:
                    logger.info(f"[微信Token] DCL 缓存命中: app_id={app_id}")
                    return cached_token
            
            # 4. 调用微信 API 获取新 Token
            logger.info(f"[微信Token] 请求新 Token: app_id={app_id}")
            token = await cls._fetch_access_token_from_wechat(app_id, app_secret)
            
            # 5. 缓存新 Token
            await cache.set_wechat_token(app_id, token, cls.TOKEN_CACHE_EXPIRE)
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
        
        async with httpx.AsyncClient(timeout=10.0) as client:
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
        force_refresh: bool = False
    ) -> str:
        """
        获取微信 access_token（同步版本，用于 Celery 任务）
        
        Args:
            app_id: 小程序 AppID
            app_secret: 小程序 AppSecret
            force_refresh: 是否强制刷新
            
        Returns:
            access_token
        """
        import time
        import httpx
        
        if not app_id or not app_secret:
            raise ValueError("微信配置不完整")
        
        # 1. 尝试从缓存获取
        if not force_refresh:
            cached_token = sync_cache.get_wechat_token(app_id)
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
            cached_token = sync_cache.get_wechat_token(app_id)
            if cached_token:
                return cached_token
            raise ValueError("获取微信 Token 失败：无法获取分布式锁")
        
        try:
            # 3. 双重检查
            if not force_refresh:
                cached_token = sync_cache.get_wechat_token(app_id)
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
            sync_cache.set_wechat_token(app_id, token, cls.TOKEN_CACHE_EXPIRE)
            logger.info(f"[微信Token] 同步已缓存新 Token: app_id={app_id}")
            
            return token
            
        finally:
            SyncRedisCache.release_lock(lock_name, lock_value)


class WechatService:
    """微信小程序服务
    
    支持从门店读取独立的微信配置，每个门店可以有独立的小程序。
    """
    
    WECHAT_API_URL = "https://api.weixin.qq.com"
    
    def __init__(self, db: AsyncSession, store_id: Optional[str] = None):
        """
        初始化微信服务
        
        Args:
            db: 数据库会话
            store_id: 门店ID，如果提供则从该门店读取微信配置
        """
        self.db = db
        self.store_id = store_id
        self._app_id: Optional[str] = None
        self._app_secret: Optional[str] = None
        self._config_loaded = False
    
    async def _load_config(self):
        """加载微信配置（从门店读取）"""
        if self._config_loaded:
            return
        
        # 优先从环境变量读取（开发/测试环境兼容）
        if settings.WECHAT_APP_ID and settings.WECHAT_APP_SECRET:
            self._app_id = settings.WECHAT_APP_ID
            self._app_secret = settings.WECHAT_APP_SECRET
            self._config_loaded = True
            return
        
        # 从门店读取微信配置
        if self.store_id:
            from app.models.store import Store
            from sqlalchemy import select
            
            result = await self.db.execute(
                select(Store).where(Store.id == self.store_id)
            )
            store = result.scalar_one_or_none()
            
            if store and store.wechat_app_id and store.wechat_app_secret:
                self._app_id = store.wechat_app_id
                self._app_secret = store.wechat_app_secret
                self._config_loaded = True
                logger.debug(f"[微信配置] 从门店加载: store_id={self.store_id}")
                return
        
        # 未找到配置
        self._config_loaded = True
        logger.warning(f"[微信配置] 未找到配置: store_id={self.store_id}")
    
    async def code2session(self, code: str) -> Dict[str, Any]:
        """
        通过 code 获取 session_key 和 openid
        https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/user-login/code2Session.html
        """
        await self._load_config()
        
        if not self._app_id or not self._app_secret:
            raise ValueError("微信配置不完整，请先在系统设置中配置 AppID 和 Secret")
        
        url = f"{self.WECHAT_API_URL}/sns/jscode2session"
        params = {
            "appid": self._app_id,
            "secret": self._app_secret,
            "js_code": code,
            "grant_type": "authorization_code"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            data = response.json()
        
        if "errcode" in data and data["errcode"] != 0:
            error_msg = data.get("errmsg", "微信登录失败")
            logger.error(f"微信登录失败: {error_msg}, code={code}")
            raise ValueError(f"微信登录失败: {error_msg}")
        
        return {
            "openid": data.get("openid"),
            "session_key": data.get("session_key"),
            "unionid": data.get("unionid"),
        }
    
    async def get_phone_number(self, code: str) -> Optional[str]:
        """
        通过 code 获取用户手机号
        https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/user-info/phone-number/getPhoneNumber.html
        """
        await self._load_config()
        
        # 获取 access_token（使用 TokenManager）
        access_token = await WechatTokenManager.get_access_token(
            self._app_id,
            self._app_secret
        )
        
        url = f"{self.WECHAT_API_URL}/wxa/business/getuserphonenumber?access_token={access_token}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json={"code": code})
            data = response.json()
        
        if data.get("errcode", 0) != 0:
            logger.warning(f"获取手机号失败: {data.get('errmsg')}")
            return None
        
        phone_info = data.get("phone_info", {})
        return phone_info.get("purePhoneNumber") or phone_info.get("phoneNumber")
    
    async def get_access_token(self) -> str:
        """获取 access_token（对外接口）"""
        await self._load_config()
        return await WechatTokenManager.get_access_token(
            self._app_id,
            self._app_secret
        )
    
    async def refresh_access_token(self) -> str:
        """强制刷新 access_token"""
        await self._load_config()
        return await WechatTokenManager.get_access_token(
            self._app_id,
            self._app_secret,
            force_refresh=True
        )
    
    async def send_subscribe_message(
        self,
        openid: str,
        template_id: str,
        data: Dict[str, Any],
        page: str = None
    ) -> bool:
        """
        发送订阅消息
        https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/mp-message-management/subscribe-message/sendMessage.html
        
        Args:
            openid: 用户 openid
            template_id: 模板 ID
            data: 模板数据
            page: 点击跳转的页面
            
        Returns:
            是否发送成功
        """
        await self._load_config()
        access_token = await WechatTokenManager.get_access_token(
            self._app_id,
            self._app_secret
        )
        
        url = f"{self.WECHAT_API_URL}/cgi-bin/message/subscribe/send?access_token={access_token}"
        
        payload = {
            "touser": openid,
            "template_id": template_id,
            "data": data
        }
        if page:
            payload["page"] = page
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            result = response.json()
        
        if result.get("errcode", 0) != 0:
            error_code = result.get("errcode")
            # 如果是 Token 过期错误，尝试刷新后重试
            if error_code in [40001, 42001]:
                logger.warning(f"Token 可能过期，尝试刷新: errcode={error_code}")
                access_token = await WechatTokenManager.get_access_token(
                    self._app_id,
                    self._app_secret,
                    force_refresh=True
                )
                url = f"{self.WECHAT_API_URL}/cgi-bin/message/subscribe/send?access_token={access_token}"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(url, json=payload)
                    result = response.json()
                
                if result.get("errcode", 0) != 0:
                    logger.error(f"发送订阅消息失败（重试后）: {result.get('errmsg')}, openid={openid}")
                    return False
            else:
                logger.error(f"发送订阅消息失败: {result.get('errmsg')}, openid={openid}")
                return False
        
        logger.info(f"订阅消息发送成功: openid={openid}, template={template_id}")
        return True
