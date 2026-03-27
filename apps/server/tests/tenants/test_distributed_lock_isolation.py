"""
分布式锁租户隔离测试

测试租户级别的分布式锁隔离，确保：
1. 同一资源ID 在不同租户下可以获取各自的锁
2. 锁键格式包含 tenant_id 维度
3. 租户隔离的锁不会互相影响
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.redis import RedisCache
from app.middleware.tenant_context import set_tenant_context, clear_tenant_context


@pytest_asyncio.fixture
async def redis_client():
    """创建 Redis 客户端 Mock"""
    from redis.asyncio import Redis
    client = AsyncMock(spec=Redis)
    client.get.return_value = "mock_value"
    client.set.return_value = True
    client.eval.return_value = 1
    client.delete.return_value = True
    client.keys.return_value = []
    client.scan.return_value = (0, [])
    yield client


@pytest_asyncio.fixture
def tenant_a():
    """创建测试租户A"""
    from app.models.tenant import Tenant
    tenant = Tenant(
        id="tenant-a-id",
        tenant_code="tenant_a",
        name="租户A",
        status=1
    )
    return tenant


@pytest_asyncio.fixture
def tenant_b():
    """创建测试租户B"""
    from app.models.tenant import Tenant
    tenant = Tenant(
        id="tenant-b-id",
        tenant_code="tenant_b",
        name="租户B",
        status=1
    )
    return tenant


@pytest.mark.asyncio
class TestDistributedLockTenantIsolation:
    """测试分布式锁的租户隔离

    场景：两个租户同时操作同一资源ID
    预期：分布式锁按租户隔离，锁键互不影响
    """

    async def test_lock_key_format_with_tenant(self, redis_client, tenant_a, tenant_b):
        """测试锁键格式包含租户维度

        场景：创建两个租户的锁
        预期: 锁键格式应为 tenant:{tenant_id}:{resource_id}
        """
        # 验证租户隔离的锁键格式
        tenant_aware_lock_a = RedisCache._build_tenant_aware_lock_name(
            "appointment:create", tenant_a.id
        )
        assert tenant_aware_lock_a == f"tenant:{tenant_a.id}:appointment:create"

        tenant_aware_lock_b = RedisCache._build_tenant_aware_lock_name(
            "appointment:create", tenant_b.id
        )
        assert tenant_aware_lock_b == f"tenant:{tenant_b.id}:appointment:create"

        # 恢复租户上下文
        clear_tenant_context()

    @pytest.mark.skip(reason="SyncRedisCache 不需要租户隔离方法，使用异步版本即可")
    async def test_sync_lock_tenant_isolation(self, redis_client, tenant_a, tenant_b):
        """测试同步版本的租户隔离锁 - 已跳过

        """
        pass


class TestCacheIsolationEdgeCases:
    """测试缓存隔离边界情况"""

    async def test_lock_with_no_tenant_context(self, redis_client):
        """测试无租户上下文时的锁行为

        场景: 没有租户上下文时获取锁
        预期: 锁键应该不包含租户ID
        """
        clear_tenant_context()

        lock_name = "appointment:create"

        # 检查无租户时使用原始锁键
        lock_key = RedisCache._build_tenant_aware_lock_name(lock_name, None)
        # 无租户时应该返回原始锁名称
        assert lock_key == lock_name

        # 清理
        clear_tenant_context()


@pytest.mark.asyncio
class TestAppointmentLockTenantIsolation:
    """预约分布式锁租户隔离测试

    验证 service_booking.py 中预约创建和取消使用的
    tenant_distributed_lock 在不同租户下使用不同的锁 key。
    """

    def test_appointment_create_lock_keys_isolated_by_tenant(self):
        """测试预约创建锁在不同租户间使用不同的 key

        场景：两个租户对同一 schedule_id 发起预约创建
        预期：锁 key 包含各自的 tenant_id，互不影响
        """
        schedule_id = "schedule-123"

        # 模拟 service_booking.py 中构建 lock_name 的逻辑
        lock_name = f"appointment:create:{schedule_id}"

        # 两个租户的锁 key
        lock_key_a = RedisCache._build_tenant_aware_lock_name(lock_name, "tenant-a-id")
        lock_key_b = RedisCache._build_tenant_aware_lock_name(lock_name, "tenant-b-id")

        assert lock_key_a == f"tenant:tenant-a-id:{lock_name}"
        assert lock_key_b == f"tenant:tenant-b-id:{lock_name}"
        assert lock_key_a != lock_key_b, (
            "同一 schedule_id 的预约创建锁在不同租户下应使用不同的 key"
        )

    def test_appointment_cancel_lock_keys_isolated_by_tenant(self):
        """测试预约取消锁在不同租户间使用不同的 key

        场景：两个租户取消同一 schedule_id 下的预约
        预期：锁 key 包含各自的 tenant_id，互不影响
        """
        schedule_id = "schedule-456"
        lock_name = f"appointment:cancel:{schedule_id}"

        lock_key_a = RedisCache._build_tenant_aware_lock_name(lock_name, "tenant-a-id")
        lock_key_b = RedisCache._build_tenant_aware_lock_name(lock_name, "tenant-b-id")

        assert lock_key_a == f"tenant:tenant-a-id:{lock_name}"
        assert lock_key_b == f"tenant:tenant-b-id:{lock_name}"
        assert lock_key_a != lock_key_b

    def test_appointment_lock_same_tenant_consistent_key(self):
        """测试同一租户内同一资源的锁 key 一致

        场景：同一租户多次构建锁 key
        预期：每次生成的 key 相同
        """
        schedule_id = "schedule-789"
        lock_name = f"appointment:create:{schedule_id}"

        key_1 = RedisCache._build_tenant_aware_lock_name(lock_name, "tenant-x-id")
        key_2 = RedisCache._build_tenant_aware_lock_name(lock_name, "tenant-x-id")

        assert key_1 == key_2, "同一租户同一资源的锁 key 应该一致"

    def test_appointment_lock_different_schedule_same_tenant(self):
        """测试同一租户不同 schedule 的锁 key 不同

        场景：同一租户对不同 schedule 创建预约
        预期：锁 key 不同
        """
        lock_name_1 = "appointment:create:schedule-111"
        lock_name_2 = "appointment:create:schedule-222"

        key_1 = RedisCache._build_tenant_aware_lock_name(lock_name_1, "tenant-a-id")
        key_2 = RedisCache._build_tenant_aware_lock_name(lock_name_2, "tenant-a-id")

        assert key_1 != key_2, "不同 schedule 的锁 key 应该不同"

    async def test_tenant_distributed_lock_context_manager_uses_tenant_key(self):
        """测试 tenant_distributed_lock 上下文管理器使用租户隔离的 key

        场景：使用 tenant_distributed_lock 获取锁
        预期：实际调用的 acquire_lock 使用了包含 tenant_id 的 key
        """
        tenant_id = "test-tenant-isolation"
        lock_name = "appointment:create:schedule-test"

        with patch.object(RedisCache, "acquire_lock", new_callable=AsyncMock, return_value="lock-uuid") as mock_acquire, \
             patch.object(RedisCache, "release_lock", new_callable=AsyncMock, return_value=True) as mock_release:

            async with RedisCache.tenant_distributed_lock(lock_name, tenant_id=tenant_id, timeout=5, retry_times=1):
                pass

            # 验证 acquire_lock 被调用时使用了包含 tenant_id 的 key
            mock_acquire.assert_called_once()
            actual_key = mock_acquire.call_args[0][0]
            assert f"tenant:{tenant_id}:" in actual_key, (
                f"锁 key 应包含 tenant:{tenant_id}: 前缀，实际为: {actual_key}"
            )

            # 验证 release_lock 也使用了相同的 key
            mock_release.assert_called_once()
            release_key = mock_release.call_args[0][0]
            assert release_key == actual_key, "释放锁的 key 应与获取锁的 key 相同"

    def test_lock_from_tenant_context_when_no_explicit_id(self):
        """测试未显式传入 tenant_id 时从上下文获取

        场景：tenant_distributed_lock 未传入 tenant_id
        预期：从当前租户上下文获取 tenant_id
        """
        lock_name = "appointment:create:schedule-ctx"

        # 设置租户上下文
        set_tenant_context("context-tenant-id")
        try:
            key = RedisCache._build_tenant_aware_lock_name(lock_name)
            assert "context-tenant-id" in key, (
                "应从上下文获取 tenant_id 并包含在锁 key 中"
            )
        finally:
            clear_tenant_context()
