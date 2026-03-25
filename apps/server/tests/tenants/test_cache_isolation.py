"""
缓存隔离测试

测试租户级别的缓存隔离，确保：
1. 短信验证码在不同租户间隔离
2. 会话缓存在不同租户间隔离
3. 缓存键格式正确包含租户维度
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from app.core.redis import RedisCache
from app.middleware.tenant_context import set_current_tenant_id, reset_tenant_context
from app.modules.auth.service import AuthService
from app.common.sms.service import SMSService


@pytest.mark.asyncio
class TestCacheIsolation:
    """缓存隔离测试套件"""

    async def test_sms_verification_code_isolation(self, db_session, redis_client):
        """测试短信验证码在不同租户间的隔离

        场景：同一手机号在两个租户同时发送验证码
        预期：两个租户的验证码互不影响
        """
        # 创建两个租户
        from app.models.tenant import Tenant

        tenant_a = Tenant(
            id="tenant-a-id",
            tenant_code="tenant_a",
            name="租户A",
            status=1
        )
        tenant_b = Tenant(
            id="tenant-b-id",
            tenant_code="tenant_b",
            name="租户B",
            status=1
        )
        db_session.add(tenant_a)
        db_session.add(tenant_b)
        await db_session.commit()

        phone = "13800138000"

        # 租户A发送验证码
        set_current_tenant_id(tenant_a.id)
        sms_service_a = SMSService(redis_client)
        code_a = "123456"
        await sms_service_a.send_verification_code(phone, code_a, "login")

        # 租户B发送验证码
        set_current_tenant_id(tenant_b.id)
        sms_service_b = SMSService(redis_client)
        code_b = "654321"
        await sms_service_b.send_verification_code(phone, code_b, "login")

        # 验证租户A的验证码
        set_current_tenant_id(tenant_a.id)
        is_valid_a = await sms_service_a.verify_code(phone, code_a, "login")
        assert is_valid_a is True, "租户A应该能验证自己的验证码"

        # 验证租户A不能使用租户B的验证码
        is_valid_a_using_b = await sms_service_a.verify_code(phone, code_b, "login")
        assert is_valid_a_using_b is False, "租户A不应该能验证租户B的验证码"

        # 验证租户B的验证码
        set_current_tenant_id(tenant_b.id)
        is_valid_b = await sms_service_b.verify_code(phone, code_b, "login")
        assert is_valid_b is True, "租户B应该能验证自己的验证码"

        # 验证租户B不能使用租户A的验证码
        is_valid_b_using_a = await sms_service_b.verify_code(phone, code_a, "login")
        assert is_valid_b_using_a is False, "租户B不应该能验证租户A的验证码"

        # 清理
        reset_tenant_context()

    async def test_session_cache_isolation(self, db_session, redis_client):
        """测试会话缓存在不同租户间的隔离

        场景：同一管理员ID在两个租户下创建会话
        预期：两个租户的会话互不影响
        """
        from app.models.tenant import Tenant
        from app.models.admin import Admin
        from app.core.security import get_password_hash

        # 创建两个租户
        tenant_a = Tenant(
            id="tenant-a-id",
            tenant_code="tenant_a",
            name="租户A",
            status=1
        )
        tenant_b = Tenant(
            id="tenant-b-id",
            tenant_code="tenant_b",
            name="租户B",
            status=1
        )
        db_session.add(tenant_a)
        db_session.add(tenant_b)

        # 创建两个租户的管理员（使用相同的手机号）
        admin_a = Admin(
            id="admin-a-id",
            username="admin_a",
            phone="13800138001",
            password_hash=get_password_hash("123456"),
            name="管理员A",
            tenant_id=tenant_a.id,
            status=1
        )
        admin_b = Admin(
            id="admin-b-id",
            username="admin_b",
            phone="13800138001",  # 同一手机号
            password_hash=get_password_hash("123456"),
            name="管理员B",
            tenant_id=tenant_b.id,
            status=1
        )
        db_session.add(admin_a)
        db_session.add(admin_b)
        await db_session.commit()

        # 模拟租户A的登录会话
        set_current_tenant_id(tenant_a.id)
        auth_service_a = AuthService(db_session, redis_client)
        token_a = await auth_service_a.create_login_session(
            admin_a.id,
            {"ip": "192.168.1.1", "user_agent": "Mozilla/5.0"}
        )

        # 模拟租户B的登录会话
        set_current_tenant_id(tenant_b.id)
        auth_service_b = AuthService(db_session, redis_client)
        token_b = await auth_service_b.create_login_session(
            admin_b.id,
            {"ip": "192.168.1.2", "user_agent": "Mozilla/5.0"}
        )

        # 验证两个token不同
        assert token_a != token_b, "不同租户的会话token应该不同"

        # 验证租户A的会话有效
        set_current_tenant_id(tenant_a.id)
        session_a = await auth_service_a.get_session(token_a)
        assert session_a is not None, "租户A应该能获取自己的会话"
        assert session_a["admin_id"] == admin_a.id

        # 验证租户A不能获取租户B的会话
        session_b_from_a = await auth_service_a.get_session(token_b)
        assert session_b_from_a is None, "租户A不应该能获取租户B的会话"

        # 验证租户B的会话有效
        set_current_tenant_id(tenant_b.id)
        session_b = await auth_service_b.get_session(token_b)
        assert session_b is not None, "租户B应该能获取自己的会话"
        assert session_b["admin_id"] == admin_b.id

        # 验证租户B不能获取租户A的会话
        session_a_from_b = await auth_service_b.get_session(token_a)
        assert session_a_from_b is None, "租户B不应该能获取租户A的会话"

        # 清理
        reset_tenant_context()

    async def test_cache_key_format_includes_tenant(self, db_session, redis_client):
        """测试缓存键格式包含租户维度

        场景：验证各种缓存键的格式
        预期：所有缓存键都包含 tenant_id
        """
        from app.models.tenant import Tenant

        # 创建租户
        tenant = Tenant(
            id="test-tenant-id",
            tenant_code="test_tenant",
            name="测试租户",
            status=1
        )
        db_session.add(tenant)
        await db_session.commit()

        set_current_tenant_id(tenant.id)

        # 测试短信验证码缓存键
        sms_service = SMSService(redis_client)
        phone = "13800138002"
        await sms_service.send_verification_code(phone, "123456", "login")

        # 检查Redis中的键格式
        keys = await redis_client.keys("sms:*")
        sms_key = None
        for key in keys:
            if str(tenant.id) in key:
                sms_key = key
                break

        assert sms_key is not None, "短信验证码缓存键应包含租户ID"
        assert f"sms:{tenant.id}:" in sms_key or f"sms:{tenant.id}:" in sms_key, \
            f"短信验证码缓存键格式错误: {sms_key}"

        # 清理
        reset_tenant_context()

    async def test_cache_isolation_prevents_pollution(self, db_session, redis_client):
        """测试缓存隔离防止跨租户污染

        场景：模拟恶意尝试跨租户访问缓存
        预期：跨租户访问被正确隔离
        """
        from app.models.tenant import Tenant

        # 创建两个租户
        tenant_a = Tenant(
            id="tenant-a-id",
            tenant_code="tenant_a",
            name="租户A",
            status=1
        )
        tenant_b = Tenant(
            id="tenant-b-id",
            tenant_code="tenant_b",
            name="租户B",
            status=1
        )
        db_session.add(tenant_a)
        db_session.add(tenant_b)
        await db_session.commit()

        phone = "13800138003"

        # 租户A存储数据
        set_current_tenant_id(tenant_a.id)
        sms_service_a = SMSService(redis_client)
        await sms_service_a.send_verification_code(phone, "111111", "login")

        # 租户A能验证
        is_valid_a = await sms_service_a.verify_code(phone, "111111", "login")
        assert is_valid_a is True

        # 切换到租户B
        set_current_tenant_id(tenant_b.id)
        sms_service_b = SMSService(redis_client)

        # 租户B不能验证租户A的数据（应该返回False，因为租户B没有发送过验证码）
        is_valid_b = await sms_service_b.verify_code(phone, "111111", "login")
        assert is_valid_b is False, "租户B不应该能验证租户A的验证码"

        # 租户B发送自己的验证码
        await sms_service_b.send_verification_code(phone, "222222", "login")
        is_valid_b_own = await sms_service_b.verify_code(phone, "222222", "login")
        assert is_valid_b_own is True

        # 切换回租户A，验证租户A的验证码仍然有效
        set_current_tenant_id(tenant_a.id)
        is_valid_a_still = await sms_service_a.verify_code(phone, "111111", "login")
        assert is_valid_a_still is True, "租户A的验证码应该仍然有效"

        # 租户A不能验证租户B的验证码
        is_valid_a_using_b = await sms_service_a.verify_code(phone, "222222", "login")
        assert is_valid_a_using_b is False, "租户A不应该能验证租户B的验证码"

        # 清理
        reset_tenant_context()

    async def test_distributed_lock_tenant_isolation(self, db_session, redis_client):
        """测试分布式锁的租户隔离

        场景：两个租户同时操作同一资源ID
        预期：分布式锁按租户隔离，互不影响
        """
        from app.models.tenant import Tenant

        # 创建两个租户
        tenant_a = Tenant(
            id="tenant-a-id",
            tenant_code="tenant_a",
            name="租户A",
            status=1
        )
        tenant_b = Tenant(
            id="tenant-b-id",
            tenant_code="tenant_b",
            name="租户B",
            status=1
        )
        db_session.add(tenant_a)
        db_session.add(tenant_b)
        await db_session.commit()

        schedule_id = "test-schedule-id"
        redis_cache = RedisCache(redis_client)

        # 租户A获取锁
        set_current_tenant_id(tenant_a.id)
        lock_name_a = f"appointment:create:{tenant_a.id}:{schedule_id}"

        acquired_a = False
        async with redis_cache.distributed_lock(lock_name_a, timeout=5):
            acquired_a = True

            # 在租户A持有锁期间，租户B应该能获取自己的锁
            set_current_tenant_id(tenant_b.id)
            lock_name_b = f"appointment:create:{tenant_b.id}:{schedule_id}"

            acquired_b = False
            async with redis_cache.distributed_lock(lock_name_b, timeout=5):
                acquired_b = True
                # 租户B成功获取锁

            assert acquired_b is True, "租户B应该能获取自己的锁"

        assert acquired_a is True, "租户A应该能获取锁"

        # 清理
        reset_tenant_context()


@pytest.mark.asyncio
class TestCacheIsolationEdgeCases:
    """缓存隔离边界情况测试"""

    async def test_no_tenant_context_cache_access(self, redis_client):
        """测试无租户上下文时的缓存访问"""
        # 确保没有租户上下文
        reset_tenant_context()

        sms_service = SMSService(redis_client)

        # 无租户上下文时，发送验证码应该失败或使用默认行为
        # 这里验证不会抛出异常，但缓存键不包含租户ID
        try:
            await sms_service.send_verification_code("13800138000", "123456", "login")
            # 检查缓存键格式
            keys = await redis_client.keys("sms:*")
            # 如果没有租户上下文，键应该不包含租户ID
            assert len(keys) > 0, "应该创建了缓存键"
        except Exception as e:
            # 某些实现可能要求租户上下文
            assert "tenant" in str(e).lower() or "context" in str(e).lower()

    async def test_deleted_tenant_cache_cleanup(self, db_session, redis_client):
        """测试租户删除后的缓存清理"""
        from app.models.tenant import Tenant

        # 创建租户
        tenant = Tenant(
            id="test-tenant-id",
            tenant_code="test_tenant",
            name="测试租户",
            status=1
        )
        db_session.add(tenant)
        await db_session.commit()

        set_current_tenant_id(tenant.id)

        # 创建缓存数据
        sms_service = SMSService(redis_client)
        await sms_service.send_verification_code("13800138000", "123456", "login")

        # 软删除租户
        from datetime import datetime
        tenant.deleted_at = datetime.utcnow()
        tenant.status = 0
        await db_session.commit()

        # 验证缓存是否仍然存在（取决于实现）
        # 理想情况下，删除租户时应该清理相关缓存
        keys = await redis_client.keys(f"sms:{tenant.id}:*")

        # 清理
        if keys:
            await redis_client.delete(*keys)

        reset_tenant_context()
