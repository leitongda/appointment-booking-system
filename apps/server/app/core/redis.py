"""
Redis 缓存客户端
用于验证码存储、微信 access_token 缓存、扫码登录状态、分布式锁等
"""
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

import redis as sync_redis
import redis.asyncio as aioredis

from app.core.config import settings
from app.middleware.tenant_context import get_current_tenant_id

logger = logging.getLogger(__name__)

# 异步 Redis 客户端实例（FastAPI 使用）
_redis_client: aioredis.Redis | None = None

# 同步 Redis 客户端实例（Celery 任务使用）
_sync_redis_client: sync_redis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """获取异步 Redis 客户端"""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,  # 连接超时 5 秒
            socket_timeout=5,  # 操作超时 5 秒
        )
    return _redis_client


async def close_redis():
    """关闭异步 Redis 连接"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


def get_sync_redis() -> sync_redis.Redis:
    """获取同步 Redis 客户端（用于 Celery 任务）"""
    global _sync_redis_client
    if _sync_redis_client is None:
        _sync_redis_client = sync_redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,  # 连接超时 5 秒
            socket_timeout=5,  # 操作超时 5 秒
        )
    return _sync_redis_client


def close_sync_redis():
    """关闭同步 Redis 连接"""
    global _sync_redis_client
    if _sync_redis_client:
        _sync_redis_client.close()
        _sync_redis_client = None


class RedisCache:
    """Redis 缓存操作类"""
    
    # 缓存键前缀
    PREFIX_SMS = "sms:"                    # 短信验证码
    PREFIX_EMAIL = "email:"                # 邮箱验证码
    PREFIX_WECHAT_TOKEN = "wechat:token:"  # 微信 access_token
    PREFIX_WECHAT_LOCK = "wechat:lock:"    # 微信 Token 刷新锁
    PREFIX_SCAN_LOGIN = "scan:login:"      # 扫码登录
    PREFIX_USER_SESSION = "session:"       # 用户会话
    PREFIX_ADMIN_SESSION = "session:admin:"  # 管理员会话
    PREFIX_TOKEN_BLACKLIST = "token:blacklist:"  # Token 黑名单
    PREFIX_CACHE = "cache:"                # 通用缓存
    PREFIX_LOCK = "lock:"                  # 分布式锁
    PREFIX_RULE_PERF = "rule_engine:"      # 规则引擎性能监控
    PREFIX_INTEGRATION_TOKEN = "integration:token:"  # 第三方平台 access_token
    
    @staticmethod
    async def set(key: str, value: Any, expire: int = None) -> bool:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值（自动 JSON 序列化）
            expire: 过期时间（秒）
        """
        try:
            client = await get_redis()
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            if expire:
                await client.setex(key, expire, value)
            else:
                await client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Redis SET 失败: {key}, 错误: {e}")
            return False
    
    @staticmethod
    async def get(key: str, default: Any = None) -> Any:
        """
        获取缓存
        
        Args:
            key: 缓存键
            default: 默认值
        """
        try:
            client = await get_redis()
            value = await client.get(key)
            if value is None:
                return default
            # 尝试 JSON 反序列化
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.error(f"Redis GET 失败: {key}, 错误: {e}")
            return default
    
    @staticmethod
    async def delete(key: str) -> bool:
        """删除缓存"""
        try:
            client = await get_redis()
            await client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE 失败: {key}, 错误: {e}")
            return False
    
    @staticmethod
    async def exists(key: str) -> bool:
        """检查键是否存在"""
        try:
            client = await get_redis()
            return await client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS 失败: {key}, 错误: {e}")
            return False
    
    @staticmethod
    async def ttl(key: str) -> int:
        """获取键的剩余过期时间（秒）"""
        try:
            client = await get_redis()
            return await client.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL 失败: {key}, 错误: {e}")
            return -1
    
    @staticmethod
    async def incr(key: str, amount: int = 1) -> int:
        """自增"""
        try:
            client = await get_redis()
            return await client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis INCR 失败: {key}, 错误: {e}")
            return 0

    @staticmethod
    async def expire(key: str, ttl: int) -> bool:
        """设置键的过期时间（秒）"""
        try:
            client = await get_redis()
            return await client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Redis EXPIRE 失败: {key}, 错误: {e}")
            return False

    @staticmethod
    async def zadd(key: str, mapping: dict, expire: int = None) -> int:
        """
        有序集合添加元素

        Args:
            key: 键名
            mapping: {member: score} 字典
            expire: 过期时间（秒）
        """
        try:
            client = await get_redis()
            result = await client.zadd(key, mapping)
            if expire:
                await client.expire(key, expire)
            return result
        except Exception as e:
            logger.error(f"Redis ZADD 失败: {key}, 错误: {e}")
            return 0

    @staticmethod
    async def zrangebyscore(
        key: str,
        min_score: float,
        max_score: float,
        withscores: bool = False,
        limit: int = None
    ) -> list:
        """
        有序集合按分数范围查询

        Args:
            key: 键名
            min_score: 最小分数
            max_score: 最大分数
            withscores: 是否返回分数
            limit: 返回数量限制
        """
        try:
            client = await get_redis()
            if limit:
                return await client.zrangebyscore(
                    key, min_score, max_score,
                    start=0, num=limit,
                    withscores=withscores
                )
            return await client.zrangebyscore(
                key, min_score, max_score,
                withscores=withscores
            )
        except Exception as e:
            logger.error(f"Redis ZRANGEBYSCORE 失败: {key}, 错误: {e}")
            return []

    @staticmethod
    async def lpush(key: str, *values) -> int:
        """
        列表左侧推入元素

        Args:
            key: 键名
            values: 要推入的值
        """
        try:
            client = await get_redis()
            return await client.lpush(key, *values)
        except Exception as e:
            logger.error(f"Redis LPUSH 失败: {key}, 错误: {e}")
            return 0

    @staticmethod
    async def ltrim(key: str, start: int, stop: int) -> bool:
        """
        列表修剪

        Args:
            key: 键名
            start: 起始位置
            stop: 结束位置
        """
        try:
            client = await get_redis()
            await client.ltrim(key, start, stop)
            return True
        except Exception as e:
            logger.error(f"Redis LTRIM 失败: {key}, 错误: {e}")
            return False

    @staticmethod
    async def lrange(key: str, start: int, stop: int) -> list:
        """
        列表范围查询

        Args:
            key: 键名
            start: 起始位置
            stop: 结束位置
        """
        try:
            client = await get_redis()
            return await client.lrange(key, start, stop)
        except Exception as e:
            logger.error(f"Redis LRANGE 失败: {key}, 错误: {e}")
            return []

    @staticmethod
    async def llen(key: str) -> int:
        """
        获取列表长度

        Args:
            key: 键名
        """
        try:
            client = await get_redis()
            return await client.llen(key)
        except Exception as e:
            logger.error(f"Redis LLEN 失败: {key}, 错误: {e}")
            return 0
    
    # ==================== 短信验证码相关（多租户隔离）====================

    @classmethod
    async def set_sms_code(
        cls,
        phone: str,
        code: str,
        code_type: str = "login",
        expire: int = 300,
        tenant_id: str = None,
    ) -> bool:
        """
        存储短信验证码（支持多租户隔离）

        Args:
            phone: 手机号
            code: 验证码
            code_type: 类型（login/register/reset）
            expire: 过期时间（秒），默认 5 分钟
            tenant_id: 租户ID（用于多租户隔离）
        """
        # 构建包含租户ID的缓存键
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            key = f"{cls.PREFIX_SMS}{effective_tenant_id}:{phone}:{code_type}"
        else:
            key = f"{cls.PREFIX_SMS}{phone}:{code_type}"
        data = {
            "code": code,
            "verified": False
        }
        return await cls.set(key, data, expire)

    @classmethod
    async def get_sms_code(cls, phone: str, code_type: str = "login", tenant_id: str = None) -> dict | None:
        """获取短信验证码（支持多租户隔离）"""
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            key = f"{cls.PREFIX_SMS}{effective_tenant_id}:{phone}:{code_type}"
        else:
            key = f"{cls.PREFIX_SMS}{phone}:{code_type}"
        return await cls.get(key)

    @classmethod
    async def verify_sms_code(cls, phone: str, code: str, code_type: str = "login", tenant_id: str = None) -> bool:
        """
        验证短信验证码（支持多租户隔离）

        Returns:
            验证是否成功
        """
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            key = f"{cls.PREFIX_SMS}{effective_tenant_id}:{phone}:{code_type}"
        else:
            key = f"{cls.PREFIX_SMS}{phone}:{code_type}"
        data = await cls.get(key)

        if not data:
            return False

        if data.get("verified"):
            return False  # 已使用

        if data.get("code") != code:
            return False

        # 标记为已使用
        data["verified"] = True
        ttl = await cls.ttl(key)
        if ttl > 0:
            await cls.set(key, data, ttl)

        return True

    @classmethod
    async def check_sms_rate_limit(
        cls,
        phone: str,
        code_type: str = "login",
        interval: int = 60,
        tenant_id: str = None,
    ) -> tuple[bool, int]:
        """
        检查短信发送频率（支持多租户隔离）

        Returns:
            (是否可以发送, 剩余等待秒数)
        """
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            key = f"{cls.PREFIX_SMS}{effective_tenant_id}:{phone}:{code_type}:limit"
        else:
            key = f"{cls.PREFIX_SMS}{phone}:{code_type}:limit"
        ttl = await cls.ttl(key)

        if ttl > 0:
            return False, ttl

        # 设置发送标记
        await cls.set(key, "1", interval)
        return True, 0

    # ==================== 邮箱验证码相关（多租户隔离）====================

    @classmethod
    async def set_email_code(
        cls,
        email: str,
        code: str,
        code_type: str = "login",
        expire: int = 300,
        tenant_id: str = None,
    ) -> bool:
        """存储邮箱验证码（支持多租户隔离）"""
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            key = f"{cls.PREFIX_EMAIL}{effective_tenant_id}:{email}:{code_type}"
        else:
            key = f"{cls.PREFIX_EMAIL}{email}:{code_type}"
        data = {
            "code": code,
            "verified": False,
        }
        return await cls.set(key, data, expire)

    @classmethod
    async def get_email_code(cls, email: str, code_type: str = "login", tenant_id: str = None) -> dict | None:
        """获取邮箱验证码（支持多租户隔离）"""
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            key = f"{cls.PREFIX_EMAIL}{effective_tenant_id}:{email}:{code_type}"
        else:
            key = f"{cls.PREFIX_EMAIL}{email}:{code_type}"
        return await cls.get(key)

    @classmethod
    async def verify_email_code(cls, email: str, code: str, code_type: str = "login", tenant_id: str = None) -> bool:
        """验证邮箱验证码（支持多租户隔离）"""
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            key = f"{cls.PREFIX_EMAIL}{effective_tenant_id}:{email}:{code_type}"
        else:
            key = f"{cls.PREFIX_EMAIL}{email}:{code_type}"
        data = await cls.get(key)

        if not data:
            return False

        if data.get("verified"):
            return False  # 已使用

        if data.get("code") != code:
            return False

        # 标记为已使用
        data["verified"] = True
        ttl = await cls.ttl(key)
        if ttl > 0:
            await cls.set(key, data, ttl)

        return True

    @classmethod
    async def check_email_rate_limit(
        cls,
        email: str,
        code_type: str = "login",
        interval: int = 60,
        tenant_id: str = None,
    ) -> tuple[bool, int]:
        """检查邮箱验证码发送频率（支持多租户隔离）

        Returns:
            (是否可以发送, 剩余等待秒数)
        """
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            key = f"{cls.PREFIX_EMAIL}{effective_tenant_id}:{email}:{code_type}:limit"
        else:
            key = f"{cls.PREFIX_EMAIL}{email}:{code_type}:limit"
        ttl = await cls.ttl(key)

        if ttl > 0:
            return False, ttl

        # 设置发送标记
        await cls.set(key, "1", interval)
        return True, 0

    # ==================== 微信 Token 相关（多租户隔离）====================

    @staticmethod
    def _build_wechat_token_key(app_id: str, tenant_id: str | None = None) -> str:
        """构建微信 Token 的 Redis 键（支持多租户隔离）

        Args:
            app_id: 小程序 AppID
            tenant_id: 租户ID（可选，不传则从上下文获取）

        Returns:
            包含租户维度的键，格式: wechat:token:{tenant_id}:{app_id}
            如果没有租户上下文，则返回: wechat:token:{app_id}
        """
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            return f"{RedisCache.PREFIX_WECHAT_TOKEN}{effective_tenant_id}:{app_id}"
        return f"{RedisCache.PREFIX_WECHAT_TOKEN}{app_id}"

    @classmethod
    async def set_wechat_token(
        cls,
        app_id: str,
        token: str,
        expire: int = 7000,
        tenant_id: str | None = None,
    ) -> bool:
        """
        缓存微信 access_token（支持多租户隔离）

        Args:
            app_id: 小程序 AppID
            token: access_token
            expire: 过期时间，默认 7000 秒（token 有效期 7200 秒）
            tenant_id: 租户ID（可选，不传则从上下文获取）
        """
        key = cls._build_wechat_token_key(app_id, tenant_id)
        return await cls.set(key, token, expire)

    @classmethod
    async def get_wechat_token(cls, app_id: str, tenant_id: str | None = None) -> str | None:
        """获取微信 access_token（支持多租户隔离）

        Args:
            app_id: 小程序 AppID
            tenant_id: 租户ID（可选，不传则从上下文获取）
        """
        key = cls._build_wechat_token_key(app_id, tenant_id)
        return await cls.get(key)

    # ==================== 第三方集成 Token 缓存 ====================

    @staticmethod
    def _build_integration_token_key(provider: str, app_id: str, tenant_id: str | None = None) -> str:
        """构建第三方平台 access_token 的 Redis 键（多租户隔离）

        格式: integration:token:{tenant_id}:{provider}:{app_id}
        """
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            return f"{RedisCache.PREFIX_INTEGRATION_TOKEN}{effective_tenant_id}:{provider}:{app_id}"
        return f"{RedisCache.PREFIX_INTEGRATION_TOKEN}{provider}:{app_id}"

    @classmethod
    async def set_integration_token(
        cls,
        provider: str,
        app_id: str,
        token: str,
        expire: int = 7000,
        tenant_id: str | None = None,
    ) -> bool:
        """缓存第三方平台 access_token（钉钉/企业微信/飞书）"""
        key = cls._build_integration_token_key(provider, app_id, tenant_id)
        return await cls.set(key, token, expire)

    @classmethod
    async def get_integration_token(
        cls,
        provider: str,
        app_id: str,
        tenant_id: str | None = None,
    ) -> str | None:
        """获取第三方平台 access_token"""
        key = cls._build_integration_token_key(provider, app_id, tenant_id)
        return await cls.get(key)

    # ==================== 扫码登录相关 ====================
    
    @classmethod
    async def set_scan_login(
        cls, 
        scan_id: str, 
        data: dict, 
        expire: int = 300
    ) -> bool:
        """
        设置扫码登录状态
        
        Args:
            scan_id: 扫码 ID
            data: 状态数据 {"status": "pending/scanned/confirmed", "user_id": ...}
            expire: 过期时间，默认 5 分钟
        """
        key = f"{cls.PREFIX_SCAN_LOGIN}{scan_id}"
        return await cls.set(key, data, expire)
    
    @classmethod
    async def get_scan_login(cls, scan_id: str) -> dict | None:
        """获取扫码登录状态"""
        key = f"{cls.PREFIX_SCAN_LOGIN}{scan_id}"
        return await cls.get(key)
    
    @classmethod
    async def delete_scan_login(cls, scan_id: str) -> bool:
        """删除扫码登录状态"""
        key = f"{cls.PREFIX_SCAN_LOGIN}{scan_id}"
        return await cls.delete(key)
    
    # ==================== 管理员会话管理（多租户隔离）====================

    @staticmethod
    def _build_admin_session_key(admin_id: str, tenant_id: str | None = None) -> str:
        """构建管理员会话的 Redis 键（支持多租户隔离）

        Args:
            admin_id: 管理员 ID
            tenant_id: 租户ID（可选，不传则从上下文获取）

        Returns:
            包含租户维度的键，格式: session:admin:{tenant_id}:{admin_id}
            如果没有租户上下文（平台管理员），则返回: session:admin:{admin_id}
        """
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            return f"{RedisCache.PREFIX_ADMIN_SESSION}{effective_tenant_id}:{admin_id}"
        return f"{RedisCache.PREFIX_ADMIN_SESSION}{admin_id}"

    @classmethod
    async def set_admin_session(
        cls,
        admin_id: str,
        session_data: dict,
        expire: int = None,
        tenant_id: str | None = None,
    ) -> bool:
        """
        存储管理员会话信息（支持多租户隔离）

        Args:
            admin_id: 管理员 ID
            session_data: 会话数据，包含:
                - admin_id: 管理员 ID
                - username: 用户名
                - name: 姓名
                - role_name: 角色名称
                - login_time: 登录时间 (ISO 格式)
                - login_ip: 登录 IP
                - user_agent: User-Agent 字符串
                - token_hash: Token 的 hash 值
                - expires_at: Token 过期时间 (ISO 格式)
                - device_info: 设备信息 dict
            expire: 过期时间（秒），默认与 Token 有效期一致
            tenant_id: 租户ID（可选，用于多租户隔离，不传则从上下文获取）
        """
        key = cls._build_admin_session_key(admin_id, tenant_id)
        return await cls.set(key, session_data, expire)

    @classmethod
    async def get_admin_session(cls, admin_id: str, tenant_id: str | None = None) -> dict | None:
        """获取单个管理员会话信息（支持多租户隔离）

        Args:
            admin_id: 管理员 ID
            tenant_id: 租户ID（可选，不传则从上下文获取）
        """
        key = cls._build_admin_session_key(admin_id, tenant_id)
        return await cls.get(key)

    @classmethod
    async def get_all_admin_sessions(cls, tenant_id: str | None = None) -> list[dict]:
        """
        获取所有在线管理员会话（支持多租户隔离）

        Args:
            tenant_id: 租户ID（可选，不传则从上下文获取；平台管理员传 None 可查看所有租户）

        Returns:
            所有在线会话列表，每个元素包含会话数据和剩余 TTL
        """
        try:
            client = await get_redis()
            # 构建匹配模式：有租户上下文时仅扫描该租户的会话，否则扫描全部
            effective_tenant_id = tenant_id or get_current_tenant_id()
            if effective_tenant_id:
                pattern = f"{cls.PREFIX_ADMIN_SESSION}{effective_tenant_id}:*"
            else:
                pattern = f"{cls.PREFIX_ADMIN_SESSION}*"
            sessions = []

            cursor = 0
            while True:
                cursor, keys = await client.scan(cursor, match=pattern, count=100)
                for key in keys:
                    session_data = await cls.get(key)
                    if session_data:
                        # 获取剩余 TTL
                        ttl = await cls.ttl(key)
                        session_data["ttl"] = ttl if ttl > 0 else 0
                        sessions.append(session_data)

                if cursor == 0:
                    break

            return sessions
        except Exception as e:
            logger.error(f"获取所有管理员会话失败: {e}")
            return []

    @classmethod
    async def delete_admin_session(cls, admin_id: str, tenant_id: str | None = None) -> bool:
        """删除管理员会话（支持多租户隔离）

        Args:
            admin_id: 管理员 ID
            tenant_id: 租户ID（可选，不传则从上下文获取）
        """
        key = cls._build_admin_session_key(admin_id, tenant_id)
        return await cls.delete(key)
    
    # ==================== Token 黑名单（多租户隔离）====================

    @staticmethod
    def _build_token_blacklist_key(token_hash: str, tenant_id: str | None = None) -> str:
        """构建 Token 黑名单的 Redis 键（支持多租户隔离）

        Args:
            token_hash: Token 的 hash 值
            tenant_id: 租户ID（可选，不传则从上下文获取）

        Returns:
            包含租户维度的键，格式: token:blacklist:{tenant_id}:{token_hash}
            如果没有租户上下文（平台管理员），则返回: token:blacklist:{token_hash}
        """
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            return f"{RedisCache.PREFIX_TOKEN_BLACKLIST}{effective_tenant_id}:{token_hash}"
        return f"{RedisCache.PREFIX_TOKEN_BLACKLIST}{token_hash}"

    @classmethod
    async def add_token_to_blacklist(
        cls,
        token_hash: str,
        expire: int,
        tenant_id: str | None = None,
    ) -> bool:
        """
        将 Token 加入黑名单（支持多租户隔离）

        Args:
            token_hash: Token 的 hash 值
            expire: 过期时间（秒），应与 Token 剩余有效期一致
            tenant_id: 租户ID（可选，用于多租户隔离，不传则从上下文获取）
        """
        if expire <= 0:
            return True  # Token 已过期，无需加入黑名单
        key = cls._build_token_blacklist_key(token_hash, tenant_id)
        return await cls.set(key, "1", expire)

    @classmethod
    async def is_token_blacklisted(cls, token_hash: str, tenant_id: str | None = None) -> bool:
        """检查 Token 是否在黑名单中（支持多租户隔离）

        Args:
            token_hash: Token 的 hash 值
            tenant_id: 租户ID（可选，不传则从上下文获取）
        """
        key = cls._build_token_blacklist_key(token_hash, tenant_id)
        return await cls.exists(key)
    
    # ==================== Refresh Token 黑名单 ====================

    PREFIX_REFRESH_BLACKLIST = "refresh:blacklist:"  # Refresh Token 黑名单

    @classmethod
    async def add_refresh_token_to_blacklist(
        cls,
        token: str,
        tenant_id: str | None = None,
        ttl: int = 86400,
    ) -> bool:
        """将 Refresh Token 加入黑名单（轮换时调用）

        Args:
            token: 原始 Refresh Token 字符串
            tenant_id: 租户ID（可选，用于多租户隔离）
            ttl: 过期时间（秒），默认 24 小时

        Returns:
            是否成功
        """
        import hashlib as _hl
        token_hash = _hl.sha256(token.encode()).hexdigest()[:32]
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            key = f"{cls.PREFIX_REFRESH_BLACKLIST}{effective_tenant_id}:{token_hash}"
        else:
            key = f"{cls.PREFIX_REFRESH_BLACKLIST}{token_hash}"
        return await cls.set(key, "1", ttl)

    # ==================== 分布式锁（异步）====================

    @classmethod
    def _build_tenant_aware_lock_name(cls, lock_name: str, tenant_id: str | None = None) -> str:
        """构建包含租户维度的锁名称

        Args:
            lock_name: 原始锁名称
            tenant_id: 租户ID（可选，不传则从上下文获取）

        Returns:
            包含租户维度的锁名称，格式: tenant:{tenant_id}:{lock_name}
            如果没有租户上下文，则返回原始锁名称
        """
        if tenant_id is None:
            from app.middleware.tenant_context import get_current_tenant_id
            tenant_id = get_current_tenant_id()

        if tenant_id:
            return f"tenant:{tenant_id}:{lock_name}"
        return lock_name

    @classmethod
    async def acquire_tenant_lock(
        cls,
        lock_name: str,
        tenant_id: str | None = None,
        timeout: int = 10,
        retry_times: int = 3,
        retry_delay: float = 0.1
    ) -> str | None:
        """获取租户隔离的分布式锁

        自动在锁键中包含租户维度，确保不同租户的锁互不影响。

        Args:
            lock_name: 锁名称（不含租户前缀）
            tenant_id: 租户ID（可选，不传则从上下文获取）
            timeout: 锁超时时间（秒）
            retry_times: 重试次数
            retry_delay: 重试间隔（秒）

        Returns:
            成功返回锁标识符，失败返回 None
        """
        tenant_aware_name = cls._build_tenant_aware_lock_name(lock_name, tenant_id)
        return await cls.acquire_lock(tenant_aware_name, timeout, retry_times, retry_delay)

    @classmethod
    async def release_tenant_lock(cls, lock_name: str, lock_value: str, tenant_id: str | None = None) -> bool:
        """释放租户隔离的分布式锁

        Args:
            lock_name: 锁名称（不含租户前缀）
            lock_value: 锁标识符
            tenant_id: 租户ID（可选，不传则从上下文获取）

        Returns:
            是否成功释放
        """
        tenant_aware_name = cls._build_tenant_aware_lock_name(lock_name, tenant_id)
        return await cls.release_lock(tenant_aware_name, lock_value)

    @classmethod
    @asynccontextmanager
    async def tenant_distributed_lock(
        cls,
        lock_name: str,
        tenant_id: str | None = None,
        timeout: int = 10,
        retry_times: int = 3
    ):
        """租户隔离的分布式锁上下文管理器

        使用方式:
            async with RedisCache.tenant_distributed_lock("appointment:create"):
                # 执行需要互斥的操作
                pass

        锁键自动包含租户维度，不同租户的锁互不影响。
        """
        tenant_aware_name = cls._build_tenant_aware_lock_name(lock_name, tenant_id)
        lock_value = await cls.acquire_lock(tenant_aware_name, timeout, retry_times)
        if not lock_value:
            raise RuntimeError(f"无法获取分布式锁: {tenant_aware_name}")

        try:
            yield lock_value
        finally:
            await cls.release_lock(tenant_aware_name, lock_value)

    @classmethod
    async def acquire_lock(
        cls,
        lock_name: str,
        timeout: int = 10,
        retry_times: int = 3,
        retry_delay: float = 0.1
    ) -> str | None:
        """
        获取分布式锁（异步版本）
        
        Args:
            lock_name: 锁名称
            timeout: 锁超时时间（秒）
            retry_times: 重试次数
            retry_delay: 重试间隔（秒）
            
        Returns:
            成功返回锁标识符，失败返回 None
        """
        lock_key = f"{cls.PREFIX_LOCK}{lock_name}"
        lock_value = str(uuid.uuid4())
        
        for _ in range(retry_times):
            try:
                client = await get_redis()
                # 使用 SET NX EX 原子操作获取锁
                acquired = await client.set(
                    lock_key,
                    lock_value,
                    ex=timeout,
                    nx=True
                )
                if acquired:
                    logger.debug(f"获取锁成功: {lock_name}, value={lock_value}")
                    return lock_value
                
                # 等待后重试
                import asyncio
                await asyncio.sleep(retry_delay)
            except Exception as e:
                logger.error(f"获取锁失败: {lock_name}, 错误: {e}")
                return None
        
        logger.warning(f"获取锁超时: {lock_name}")
        return None
    
    @classmethod
    async def release_lock(cls, lock_name: str, lock_value: str) -> bool:
        """
        释放分布式锁（异步版本）
        
        使用 Lua 脚本确保只释放自己持有的锁
        
        Args:
            lock_name: 锁名称
            lock_value: 锁标识符（acquire_lock 返回的值）
            
        Returns:
            是否成功释放
        """
        lock_key = f"{cls.PREFIX_LOCK}{lock_name}"
        
        # Lua 脚本：只有锁的值匹配时才删除
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        try:
            client = await get_redis()
            result = await client.eval(lua_script, 1, lock_key, lock_value)
            if result:
                logger.debug(f"释放锁成功: {lock_name}")
                return True
            else:
                logger.warning(f"释放锁失败（锁已过期或被其他进程持有）: {lock_name}")
                return False
        except Exception as e:
            logger.error(f"释放锁异常: {lock_name}, 错误: {e}")
            return False
    
    @classmethod
    @asynccontextmanager
    async def distributed_lock(
        cls,
        lock_name: str,
        timeout: int = 10,
        retry_times: int = 3
    ):
        """
        分布式锁上下文管理器（异步）
        
        使用方式:
            async with RedisCache.distributed_lock("my_lock"):
                # 执行需要互斥的操作
                pass
        """
        lock_value = await cls.acquire_lock(lock_name, timeout, retry_times)
        if not lock_value:
            raise RuntimeError(f"无法获取分布式锁: {lock_name}")
        
        try:
            yield lock_value
        finally:
            await cls.release_lock(lock_name, lock_value)


# ==================== 同步版本（Celery 任务使用）====================

class SyncRedisCache:
    """同步 Redis 缓存操作类（用于 Celery 任务）"""
    
    PREFIX_LOCK = "lock:"
    PREFIX_WECHAT_TOKEN = "wechat:token:"
    PREFIX_WECHAT_LOCK = "wechat:lock:"
    
    @staticmethod
    def set(key: str, value: Any, expire: int = None) -> bool:
        """设置缓存（同步）"""
        try:
            client = get_sync_redis()
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            if expire:
                client.setex(key, expire, value)
            else:
                client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Redis SET 失败: {key}, 错误: {e}")
            return False
    
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """获取缓存（同步）"""
        try:
            client = get_sync_redis()
            value = client.get(key)
            if value is None:
                return default
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.error(f"Redis GET 失败: {key}, 错误: {e}")
            return default
    
    @staticmethod
    def delete(key: str) -> bool:
        """删除缓存（同步）"""
        try:
            client = get_sync_redis()
            client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE 失败: {key}, 错误: {e}")
            return False
    
    @classmethod
    def acquire_lock(
        cls,
        lock_name: str,
        timeout: int = 10,
        retry_times: int = 3,
        retry_delay: float = 0.1
    ) -> str | None:
        """获取分布式锁（同步版本）"""
        lock_key = f"{cls.PREFIX_LOCK}{lock_name}"
        lock_value = str(uuid.uuid4())
        
        for _ in range(retry_times):
            try:
                client = get_sync_redis()
                acquired = client.set(lock_key, lock_value, ex=timeout, nx=True)
                if acquired:
                    logger.debug(f"获取锁成功: {lock_name}")
                    return lock_value
                time.sleep(retry_delay)
            except Exception as e:
                logger.error(f"获取锁失败: {lock_name}, 错误: {e}")
                return None
        
        logger.warning(f"获取锁超时: {lock_name}")
        return None
    
    @classmethod
    def release_lock(cls, lock_name: str, lock_value: str) -> bool:
        """释放分布式锁（同步版本）"""
        lock_key = f"{cls.PREFIX_LOCK}{lock_name}"
        
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        try:
            client = get_sync_redis()
            result = client.eval(lua_script, 1, lock_key, lock_value)
            return bool(result)
        except Exception as e:
            logger.error(f"释放锁异常: {lock_name}, 错误: {e}")
            return False
    
    @staticmethod
    def _build_wechat_token_key(app_id: str, tenant_id: str | None = None) -> str:
        """构建微信 Token 的 Redis 键（支持多租户隔离）

        注意: 同步版本用于 Celery 任务，没有 ContextVar 上下文，
        只能通过显式传参传入 tenant_id。

        Args:
            app_id: 小程序 AppID
            tenant_id: 租户ID（可选）
        """
        if tenant_id:
            return f"{SyncRedisCache.PREFIX_WECHAT_TOKEN}{tenant_id}:{app_id}"
        return f"{SyncRedisCache.PREFIX_WECHAT_TOKEN}{app_id}"

    @classmethod
    def set_wechat_token(cls, app_id: str, token: str, expire: int = 7000, tenant_id: str | None = None) -> bool:
        """缓存微信 access_token（同步，支持多租户隔离）"""
        key = cls._build_wechat_token_key(app_id, tenant_id)
        return cls.set(key, token, expire)

    @classmethod
    def get_wechat_token(cls, app_id: str, tenant_id: str | None = None) -> str | None:
        """获取微信 access_token（同步，支持多租户隔离）"""
        key = cls._build_wechat_token_key(app_id, tenant_id)
        return cls.get(key)


# 快捷方法
cache = RedisCache()
sync_cache = SyncRedisCache()


# ==================== User-Agent 解析辅助函数 ====================

def parse_user_agent(user_agent_string: str) -> dict:
    """
    解析 User-Agent 字符串，提取设备信息
    
    Args:
        user_agent_string: User-Agent 字符串
        
    Returns:
        设备信息字典:
        - browser: 浏览器名称和版本
        - os: 操作系统名称和版本
        - device_type: 设备类型 (desktop/mobile/tablet)
    """
    try:
        from user_agents import parse
        ua = parse(user_agent_string)
        
        # 获取浏览器信息
        browser = ua.browser.family
        if ua.browser.version_string:
            browser = f"{browser} {ua.browser.version_string}"
        
        # 获取操作系统信息
        os_info = ua.os.family
        if ua.os.version_string:
            os_info = f"{os_info} {ua.os.version_string}"
        
        # 判断设备类型
        if ua.is_mobile:
            device_type = "mobile"
        elif ua.is_tablet:
            device_type = "tablet"
        else:
            device_type = "desktop"
        
        return {
            "browser": browser,
            "os": os_info,
            "device_type": device_type,
        }
    except Exception as e:
        logger.warning(f"解析 User-Agent 失败: {e}")
        return {
            "browser": "Unknown",
            "os": "Unknown",
            "device_type": "desktop",
        }

