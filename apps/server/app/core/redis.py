"""
Redis 缓存客户端
用于验证码存储、微信 access_token 缓存、扫码登录状态、分布式锁等
"""
import redis.asyncio as aioredis
import redis as sync_redis
from typing import Optional, Any
from contextlib import asynccontextmanager
import json
import logging
import uuid
import time

from app.core.config import settings

logger = logging.getLogger(__name__)

# 异步 Redis 客户端实例（FastAPI 使用）
_redis_client: Optional[aioredis.Redis] = None

# 同步 Redis 客户端实例（Celery 任务使用）
_sync_redis_client: Optional[sync_redis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """获取异步 Redis 客户端"""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
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
            decode_responses=True
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
    PREFIX_WECHAT_TOKEN = "wechat:token:"  # 微信 access_token
    PREFIX_WECHAT_LOCK = "wechat:lock:"    # 微信 Token 刷新锁
    PREFIX_SCAN_LOGIN = "scan:login:"      # 扫码登录
    PREFIX_USER_SESSION = "session:"       # 用户会话
    PREFIX_CACHE = "cache:"                # 通用缓存
    PREFIX_LOCK = "lock:"                  # 分布式锁
    
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
    
    # ==================== 短信验证码相关 ====================
    
    @classmethod
    async def set_sms_code(
        cls, 
        phone: str, 
        code: str, 
        code_type: str = "login",
        expire: int = 300
    ) -> bool:
        """
        存储短信验证码
        
        Args:
            phone: 手机号
            code: 验证码
            code_type: 类型（login/register/reset）
            expire: 过期时间（秒），默认 5 分钟
        """
        key = f"{cls.PREFIX_SMS}{phone}:{code_type}"
        data = {
            "code": code,
            "verified": False
        }
        return await cls.set(key, data, expire)
    
    @classmethod
    async def get_sms_code(cls, phone: str, code_type: str = "login") -> Optional[dict]:
        """获取短信验证码"""
        key = f"{cls.PREFIX_SMS}{phone}:{code_type}"
        return await cls.get(key)
    
    @classmethod
    async def verify_sms_code(cls, phone: str, code: str, code_type: str = "login") -> bool:
        """
        验证短信验证码
        
        Returns:
            验证是否成功
        """
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
        interval: int = 60
    ) -> tuple[bool, int]:
        """
        检查短信发送频率
        
        Returns:
            (是否可以发送, 剩余等待秒数)
        """
        key = f"{cls.PREFIX_SMS}{phone}:{code_type}:limit"
        ttl = await cls.ttl(key)
        
        if ttl > 0:
            return False, ttl
        
        # 设置发送标记
        await cls.set(key, "1", interval)
        return True, 0
    
    # ==================== 微信 Token 相关 ====================
    
    @classmethod
    async def set_wechat_token(
        cls, 
        app_id: str, 
        token: str, 
        expire: int = 7000
    ) -> bool:
        """
        缓存微信 access_token
        
        Args:
            app_id: 小程序 AppID
            token: access_token
            expire: 过期时间，默认 7000 秒（token 有效期 7200 秒）
        """
        key = f"{cls.PREFIX_WECHAT_TOKEN}{app_id}"
        return await cls.set(key, token, expire)
    
    @classmethod
    async def get_wechat_token(cls, app_id: str) -> Optional[str]:
        """获取微信 access_token"""
        key = f"{cls.PREFIX_WECHAT_TOKEN}{app_id}"
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
    async def get_scan_login(cls, scan_id: str) -> Optional[dict]:
        """获取扫码登录状态"""
        key = f"{cls.PREFIX_SCAN_LOGIN}{scan_id}"
        return await cls.get(key)
    
    @classmethod
    async def delete_scan_login(cls, scan_id: str) -> bool:
        """删除扫码登录状态"""
        key = f"{cls.PREFIX_SCAN_LOGIN}{scan_id}"
        return await cls.delete(key)
    
    # ==================== 分布式锁（异步）====================
    
    @classmethod
    async def acquire_lock(
        cls,
        lock_name: str,
        timeout: int = 10,
        retry_times: int = 3,
        retry_delay: float = 0.1
    ) -> Optional[str]:
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
    ) -> Optional[str]:
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
    
    @classmethod
    def set_wechat_token(cls, app_id: str, token: str, expire: int = 7000) -> bool:
        """缓存微信 access_token（同步）"""
        key = f"{cls.PREFIX_WECHAT_TOKEN}{app_id}"
        return cls.set(key, token, expire)
    
    @classmethod
    def get_wechat_token(cls, app_id: str) -> Optional[str]:
        """获取微信 access_token（同步）"""
        key = f"{cls.PREFIX_WECHAT_TOKEN}{app_id}"
        return cls.get(key)


# 快捷方法
cache = RedisCache()
sync_cache = SyncRedisCache()

