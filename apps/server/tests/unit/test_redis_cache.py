"""
RedisCache 单元测试

测试 Redis 缓存的核心方法：
1. set/get/delete/exists/ttl/incr - 基础操作
2. zadd/zrangebyscore - 有序集合操作
3. lpush/ltrim/lrange/llen - 列表操作
4. set_sms_code/get_sms_code/verify_sms_code - 短信验证码
5. acquire_lock/release_lock/distributed_lock - 分布式锁
6. 管理员会话管理
7. Token 黑名单
8. 扫码登录状态
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, AsyncMock
import json
from uuid import uuid4

from app.core.redis import RedisCache, SyncRedisCache


class TestBasicOperations:
    """测试基础缓存操作"""

    @pytest.mark.asyncio
    async def test_set_and_get_string(self):
        """设置和获取字符串"""
        with patch("app.core.redis.get_redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.set = AsyncMock(return_value=True)
            mock_client.get = AsyncMock(return_value="test_value")
            mock_redis.return_value = mock_client

            result = await RedisCache.set("test_key", "test_value")
            assert result is True

            value = await RedisCache.get("test_key")
            assert value == "test_value"

    @pytest.mark.asyncio
    async def test_set_and_get_dict(self):
        """设置和获取字典（自动 JSON 序列化）"""
        test_dict = {"name": "test", "value": 123}
        with patch("app.core.redis.get_redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.setex = AsyncMock(return_value=True)
            mock_client.get = AsyncMock(return_value=json.dumps(test_dict))
            mock_redis.return_value = mock_client

            result = await RedisCache.set("test_key", test_dict, expire=3600)
            assert result is True

            value = await RedisCache.get("test_key")
            assert value == test_dict

    @pytest.mark.asyncio
    async def test_get_with_default(self):
        """获取不存在的键返回默认值"""
        with patch("app.core.redis.get_redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=None)
            mock_redis.return_value = mock_client

            value = await RedisCache.get("non_existent_key", default="default_value")
            assert value == "default_value"

    @pytest.mark.asyncio
    async def test_delete(self):
        """删除缓存"""
        with patch("app.core.redis.get_redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.delete = AsyncMock(return_value=1)
            mock_redis.return_value = mock_client

            result = await RedisCache.delete("test_key")
            assert result is True

    @pytest.mark.asyncio
    async def test_exists(self):
        """检查键是否存在"""
        with patch("app.core.redis.get_redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.exists = AsyncMock(return_value=1)
            mock_redis.return_value = mock_client

            result = await RedisCache.exists("test_key")
            assert result is True

    @pytest.mark.asyncio
    async def test_ttl(self):
        """获取剩余过期时间"""
        with patch("app.core.redis.get_redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.ttl = AsyncMock(return_value=3600)
            mock_redis.return_value = mock_client

            result = await RedisCache.ttl("test_key")
            assert result == 3600

    @pytest.mark.asyncio
    async def test_incr(self):
        """自增操作"""
        with patch("app.core.redis.get_redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.incrby = AsyncMock(return_value=2)
            mock_redis.return_value = mock_client

            result = await RedisCache.incr("counter_key", amount=1)
            assert result == 2


class TestSortedSetOperations:
    """测试有序集合操作"""

    @pytest.mark.asyncio
    async def test_zadd(self):
        """添加有序集合元素"""
        with patch("app.core.redis.get_redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.zadd = AsyncMock(return_value=1)
            mock_client.expire = AsyncMock(return_value=True)
            mock_redis.return_value = mock_client

            result = await RedisCache.zadd(
                "sorted_set_key",
                {"member1": 100.0, "member2": 200.0},
                expire=3600
            )
            assert result == 1

    @pytest.mark.asyncio
    async def test_zrangebyscore(self):
        """按分数范围查询有序集合"""
        with patch("app.core.redis.get_redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.zrangebyscore = AsyncMock(
                return_value=["member1", "member2"]
            )
            mock_redis.return_value = mock_client

            result = await RedisCache.zrangebyscore(
                "sorted_set_key",
                min_score=0,
                max_score=1000
            )
            assert result == ["member1", "member2"]

    @pytest.mark.asyncio
    async def test_zrangebyscore_with_limit(self):
        """带数量限制的有序集合查询"""
        with patch("app.core.redis.get_redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.zrangebyscore = AsyncMock(return_value=["member1"])
            mock_redis.return_value = mock_client

            result = await RedisCache.zrangebyscore(
                "sorted_set_key",
                min_score=0,
                max_score=1000,
                limit=1
            )
            assert result == ["member1"]


class TestListOperations:
    """测试列表操作"""

    @pytest.mark.asyncio
    async def test_lpush(self):
        """列表左侧推入元素"""
        with patch("app.core.redis.get_redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.lpush = AsyncMock(return_value=3)
            mock_redis.return_value = mock_client

            result = await RedisCache.lpush("list_key", "item1", "item2", "item3")
            assert result == 3

    @pytest.mark.asyncio
    async def test_ltrim(self):
        """列表修剪"""
        with patch("app.core.redis.get_redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.ltrim = AsyncMock(return_value=True)
            mock_redis.return_value = mock_client

            result = await RedisCache.ltrim("list_key", 0, 99)
            assert result is True

    @pytest.mark.asyncio
    async def test_lrange(self):
        """列表范围查询"""
        with patch("app.core.redis.get_redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.lrange = AsyncMock(
                return_value=["item1", "item2", "item3"]
            )
            mock_redis.return_value = mock_client

            result = await RedisCache.lrange("list_key", 0, -1)
            assert result == ["item1", "item2", "item3"]

    @pytest.mark.asyncio
    async def test_llen(self):
        """获取列表长度"""
        with patch("app.core.redis.get_redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.llen = AsyncMock(return_value=3)
            mock_redis.return_value = mock_client

            result = await RedisCache.llen("list_key")
            assert result == 3


class TestSMSCodeOperations:
    """测试短信验证码操作"""

    @pytest.mark.asyncio
    async def test_set_sms_code(self):
        """存储短信验证码"""
        with patch.object(RedisCache, "set", new_callable=AsyncMock) as mock_set:
            mock_set.return_value = True

            result = await RedisCache.set_sms_code(
                phone="13800138000",
                code="123456",
                code_type="login",
                expire=300
            )
            assert result is True
            # 验证调用参数
            mock_set.assert_called_once()
            call_args = mock_set.call_args
            assert "sms:13800138000:login" in call_args[0][0]
            assert call_args[0][1]["code"] == "123456"
            assert call_args[0][1]["verified"] is False

    @pytest.mark.asyncio
    async def test_get_sms_code(self):
        """获取短信验证码"""
        test_data = {"code": "123456", "verified": False}
        with patch.object(RedisCache, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = test_data

            result = await RedisCache.get_sms_code("13800138000", "login")
            assert result == test_data

    @pytest.mark.asyncio
    async def test_verify_sms_code_success(self):
        """验证短信验证码成功"""
        test_data = {"code": "123456", "verified": False}
        with patch.object(RedisCache, "get", new_callable=AsyncMock) as mock_get:
            with patch.object(RedisCache, "ttl", new_callable=AsyncMock) as mock_ttl:
                with patch.object(RedisCache, "set", new_callable=AsyncMock) as mock_set:
                    mock_get.return_value = test_data
                    mock_ttl.return_value = 300
                    mock_set.return_value = True

                    result = await RedisCache.verify_sms_code(
                        phone="13800138000",
                        code="123456",
                        code_type="login"
                    )
                    assert result is True

    @pytest.mark.asyncio
    async def test_verify_sms_code_wrong_code(self):
        """验证短信验证码失败（验证码错误）"""
        test_data = {"code": "123456", "verified": False}
        with patch.object(RedisCache, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = test_data

            result = await RedisCache.verify_sms_code(
                phone="13800138000",
                code="654321",
                code_type="login"
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_verify_sms_code_already_used(self):
        """验证短信验证码失败（已使用)"""
        test_data = {"code": "123456", "verified": True}
        with patch.object(RedisCache, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = test_data

            result = await RedisCache.verify_sms_code(
                phone="13800138000",
                code="123456",
                code_type="login"
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_verify_sms_code_not_found(self):
        """验证短信验证码失败(不存在)"""
        with patch.object(RedisCache, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            result = await RedisCache.verify_sms_code(
                phone="13800138000",
                code="123456",
                code_type="login"
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_check_sms_rate_limit_allowed(self):
        """检查短信发送频率（允许发送）"""
        with patch.object(RedisCache, "ttl", new_callable=AsyncMock) as mock_ttl:
            with patch.object(RedisCache, "set", new_callable=AsyncMock) as mock_set:
                mock_ttl.return_value = -1  # 未设置发送标记
                mock_set.return_value = True

                allowed, wait_seconds = await RedisCache.check_sms_rate_limit(
                    phone="13800138000",
                    code_type="login",
                    interval=60
                )
                assert allowed is True
                assert wait_seconds == 00

    @pytest.mark.asyncio
    async def test_check_sms_rate_limit_not_allowed(self):
        """检查短信发送频率（不允许发送）"""
        with patch.object(RedisCache, "ttl", new_callable=AsyncMock) as mock_ttl:
            mock_ttl.return_value = 30  # 30 秒后才能发送

            allowed, wait_seconds = await RedisCache.check_sms_rate_limit(
                phone="13800138000",
                code_type="login",
                interval=60
            )
            assert allowed is False
            assert wait_seconds == 30


class TestDistributedLock:
    """测试分布式锁"""

    @pytest.mark.asyncio
    async def test_acquire_lock_success(self):
        """成功获取锁"""
        with patch("app.core.redis.get_redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.set = AsyncMock(return_value=True)
            mock_redis.return_value = mock_client

            lock_value = await RedisCache.acquire_lock(
                lock_name="test_lock",
                timeout=10,
                retry_times=3
            )
            assert lock_value is not None
            assert isinstance(lock_value, str)

    @pytest.mark.asyncio
    async def test_acquire_lock_failed(self):
        """获取锁失败"""
        with patch("app.core.redis.get_redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.set = AsyncMock(return_value=None)  # 锁获取失败
            mock_redis.return_value = mock_client

            lock_value = await RedisCache.acquire_lock(
                lock_name="test_lock",
                timeout=10,
                retry_times=1,
                retry_delay=0.01
            )
            assert lock_value is None

    @pytest.mark.asyncio
    async def test_release_lock_success(self):
        """成功释放锁"""
        with patch("app.core.redis.get_redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.eval = AsyncMock(return_value=1)
            mock_redis.return_value = mock_client

            result = await RedisCache.release_lock("test_lock", "lock_value")
            assert result is True

    @pytest.mark.asyncio
    async def test_release_lock_failed(self):
        """释放锁失败（锁已过期或被其他进程持有）"""
        with patch("app.core.redis.get_redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.eval = AsyncMock(return_value=0)
            mock_redis.return_value = mock_client

            result = await RedisCache.release_lock("test_lock", "lock_value")
            assert result is False

    @pytest.mark.asyncio
    async def test_distributed_lock_context_manager(self):
        """分布式锁上下文管理器"""
        with patch.object(
            RedisCache, "acquire_lock", new_callable=AsyncMock
        ) as mock_acquire:
            with patch.object(
                RedisCache, "release_lock", new_callable=AsyncMock
            ) as mock_release:
                mock_acquire.return_value = "test_lock_value"
                mock_release.return_value = True

                async with RedisCache.distributed_lock("test_lock"):
                    pass

                mock_acquire.assert_called_once_with("test_lock", 10, 3)
                mock_release.assert_called_once_with("test_lock", "test_lock_value")

    @pytest.mark.asyncio
    async def test_distributed_lock_acquire_failed(self):
        """分布式锁获取失败抛出异常"""
        with patch.object(
            RedisCache, "acquire_lock", new_callable=AsyncMock
        ) as mock_acquire:
            mock_acquire.return_value = None

            with pytest.raises(RuntimeError, match="无法获取分布式锁"):
                async with RedisCache.distributed_lock("test_lock"):
                    pass


class TestAdminSession:
    """测试管理员会话管理"""

    @pytest.mark.asyncio
    async def test_set_admin_session(self):
        """设置管理员会话"""
        session_data = {
            "admin_id": "admin-123",
            "username": "admin",
            "name": "管理员",
            "login_time": datetime.now().isoformat(),
        }
        with patch.object(RedisCache, "set", new_callable=AsyncMock) as mock_set:
            mock_set.return_value = True

            result = await RedisCache.set_admin_session(
                admin_id="admin-123",
                session_data=session_data,
                expire=3600
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_get_admin_session(self):
        """获取管理员会话"""
        session_data = {
            "admin_id": "admin-123",
            "username": "admin",
        }
        with patch.object(RedisCache, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = session_data

            result = await RedisCache.get_admin_session("admin-123")
            assert result == session_data

    @pytest.mark.asyncio
    async def test_delete_admin_session(self):
        """删除管理员会话"""
        with patch.object(RedisCache, "delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = True

            result = await RedisCache.delete_admin_session("admin-123")
            assert result is True


class TestTokenBlacklist:
    """测试 Token 黑名单"""

    @pytest.mark.asyncio
    async def test_add_token_to_blacklist(self):
        """将 Token 加入黑名单"""
        with patch.object(RedisCache, "set", new_callable=AsyncMock) as mock_set:
            mock_set.return_value = True

            result = await RedisCache.add_token_to_blacklist(
                token_hash="abc123",
                expire=3600
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_add_token_to_blacklist_expired(self):
        """已过期的 Token 不需要加入黑名单"""
        result = await RedisCache.add_token_to_blacklist(
            token_hash="abc123",
            expire=0
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_true(self):
        """Token 在黑名单中"""
        with patch.object(RedisCache, "exists", new_callable=AsyncMock) as mock_exists:
            mock_exists.return_value = True

            result = await RedisCache.is_token_blacklisted("abc123")
            assert result is True

    @pytest.mark.asyncio
    async def test_is_token_blacklisted_false(self):
        """Token 不在黑名单中"""
        with patch.object(RedisCache, "exists", new_callable=AsyncMock) as mock_exists:
            mock_exists.return_value = False

            result = await RedisCache.is_token_blacklisted("abc123")
            assert result is False


class TestScanLogin:
    """测试扫码登录状态"""

    @pytest.mark.asyncio
    async def test_set_scan_login(self):
        """设置扫码登录状态"""
        scan_data = {
            "status": "pending",
            "user_id": None,
        }
        with patch.object(RedisCache, "set", new_callable=AsyncMock) as mock_set:
            mock_set.return_value = True

            result = await RedisCache.set_scan_login(
                scan_id="scan-123",
                data=scan_data,
                expire=300
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_get_scan_login(self):
        """获取扫码登录状态"""
        scan_data = {
            "status": "scanned",
            "user_id": "user-123",
        }
        with patch.object(RedisCache, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = scan_data

            result = await RedisCache.get_scan_login("scan-123")
            assert result == scan_data

    @pytest.mark.asyncio
    async def test_delete_scan_login(self):
        """删除扫码登录状态"""
        with patch.object(RedisCache, "delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = True

            result = await RedisCache.delete_scan_login("scan-123")
            assert result is True


class TestWechatToken:
    """测试微信 Token 管理"""

    @pytest.mark.asyncio
    async def test_set_wechat_token(self):
        """缓存微信 access_token"""
        with patch.object(RedisCache, "set", new_callable=AsyncMock) as mock_set:
            mock_set.return_value = True

            result = await RedisCache.set_wechat_token(
                app_id="wx123",
                token="access_token_value",
                expire=7000
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_get_wechat_token(self):
        """获取微信 access_token"""
        with patch.object(RedisCache, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = "access_token_value"

            result = await RedisCache.get_wechat_token("wx123")
            assert result == "access_token_value"


class TestSyncRedisCache:
    """测试同步 Redis 缓存（用于 Celery 任务）"""

    def test_sync_set_and_get(self):
        """同步设置和获取"""
        with patch("app.core.redis.get_sync_redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.setex = MagicMock(return_value=True)
            mock_client.get = MagicMock(return_value="test_value")
            mock_redis.return_value = mock_client

            result = SyncRedisCache.set("test_key", "test_value", expire=3600)
            assert result is True

            value = SyncRedisCache.get("test_key")
            assert value == "test_value"

    def test_sync_delete(self):
        """同步删除"""
        with patch("app.core.redis.get_sync_redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.delete = MagicMock(return_value=1)
            mock_redis.return_value = mock_client

            result = SyncRedisCache.delete("test_key")
            assert result is True

    def test_sync_acquire_lock(self):
        """同步获取锁"""
        with patch("app.core.redis.get_sync_redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.set = MagicMock(return_value=True)
            mock_redis.return_value = mock_client

            lock_value = SyncRedisCache.acquire_lock(
                lock_name="test_lock",
                timeout=10,
                retry_times=1
            )
            assert lock_value is not None

    def test_sync_release_lock(self):
        """同步释放锁"""
        with patch("app.core.redis.get_sync_redis") as mock_redis:
            mock_client = MagicMock()
            mock_client.eval = MagicMock(return_value=1)
            mock_redis.return_value = mock_client

            result = SyncRedisCache.release_lock("test_lock", "lock_value")
            assert result is True
