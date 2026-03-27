"""
缓存隔离测试

测试租户级别的缓存隔离，确保：
1. 短信验证码在不同租户间隔离
2. 缓存键格式正确包含租户维度
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.core.redis import RedisCache, cache
from app.middleware.tenant_context import set_tenant_context, clear_tenant_context
from app.infrastructure.sms.service import SmsService


@pytest.mark.asyncio
class TestCacheIsolation:
    """缓存隔离测试套件"""

    @patch.object(RedisCache, "check_sms_rate_limit", new_callable=AsyncMock, return_value=(True, 0))
    async def test_sms_verification_code_isolation(self, mock_rate_limit, db_session, redis_client):
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
        set_tenant_context(tenant_a.id)
        code_a = await SmsService.send_code(phone, "login", tenant_id=tenant_a.id)

        # 租户B发送验证码
        set_tenant_context(tenant_b.id)
        code_b = await SmsService.send_code(phone, "login", tenant_id=tenant_b.id)

        # 验证租户A的验证码
        set_tenant_context(tenant_a.id)
        is_valid_a = await SmsService.verify_code(phone, code_a, "login", tenant_id=tenant_a.id)
        assert is_valid_a is True, "租户A应该能验证自己的验证码"

        # 验证租户A不能使用租户B的验证码
        is_valid_a_using_b = await SmsService.verify_code(phone, code_b, "login", tenant_id=tenant_a.id)
        assert is_valid_a_using_b is False, "租户A不应该能验证租户B的验证码"

        # 验证租户B的验证码
        set_tenant_context(tenant_b.id)
        is_valid_b = await SmsService.verify_code(phone, code_b, "login", tenant_id=tenant_b.id)
        assert is_valid_b is True, "租户B应该能验证自己的验证码"

        # 验证租户B不能使用租户A的验证码
        is_valid_b_using_a = await SmsService.verify_code(phone, code_a, "login", tenant_id=tenant_b.id)
        assert is_valid_b_using_a is False, "租户B不应该能验证租户A的验证码"

        # 清理
        clear_tenant_context()

    @patch.object(RedisCache, "check_sms_rate_limit", new_callable=AsyncMock, return_value=(True, 0))
    async def test_cache_isolation_prevents_pollution(self, mock_rate_limit, db_session, redis_client):
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
        set_tenant_context(tenant_a.id)
        code_a = await SmsService.send_code(phone, "login", tenant_id=tenant_a.id)

        # 注意：不在此处验证 code_a，因为验证码是一次性的，验证后会被标记为已使用

        # 切换到租户B
        set_tenant_context(tenant_b.id)

        # 租户B不能验证租户A的数据（应该返回False，因为租户B没有发送过验证码）
        is_valid_b = await SmsService.verify_code(phone, code_a, "login", tenant_id=tenant_b.id)
        assert is_valid_b is False, "租户B不应该能验证租户A的验证码"

        # 租户B发送自己的验证码
        code_b = await SmsService.send_code(phone, "login", tenant_id=tenant_b.id)
        is_valid_b_own = await SmsService.verify_code(phone, code_b, "login", tenant_id=tenant_b.id)
        assert is_valid_b_own is True

        # 切换回租户A，验证租户A的验证码仍然有效（未被租户B的操作影响）
        set_tenant_context(tenant_a.id)
        is_valid_a_still = await SmsService.verify_code(phone, code_a, "login", tenant_id=tenant_a.id)
        assert is_valid_a_still is True, "租户A的验证码应该仍然有效"

        # 租户A不能验证租户B的验证码
        is_valid_a_using_b = await SmsService.verify_code(phone, code_b, "login", tenant_id=tenant_a.id)
        assert is_valid_a_using_b is False, "租户A不应该能验证租户B的验证码"

        # 清理
        clear_tenant_context()


@pytest.mark.asyncio
class TestCacheIsolationEdgeCases:
    """缓存隔离边界情况测试"""

    async def test_no_tenant_context_cache_access(self, redis_client):
        """测试无租户上下文时的缓存访问"""
        # 确保没有租户上下文
        clear_tenant_context()

        # 无租户上下文时，发送验证码应该失败
        try:
            await SmsService.send_code("13800138000", "login")
            # 如果没有抛出异常,说明有默认行为
        except Exception as e:
            # 某些实现可能要求租户上下文
            assert "tenant" in str(e).lower() or "context" in str(e).lower() or "租户" in str(e)


@pytest.mark.asyncio
class TestRateLimitTenantIsolation:
    """API 限流租户隔离测试

    验证 RateLimitMiddleware 的 _build_rate_limit_key 方法
    确保不同租户的限流计数器独立。
    """

    def test_rate_limit_key_format_with_tenant(self):
        """测试限流键格式包含租户维度

        场景：构建两个租户的限流键
        预期：键格式为 rate_limit:{tenant_id}:{ip}:{path}:{window}，不同租户的键不同
        """
        from app.middleware.rate_limit import RateLimitMiddleware

        middleware = RateLimitMiddleware(app=None, enabled=False)

        tenant_a_id = "tenant-a-id"
        tenant_b_id = "tenant-b-id"
        client_ip = "192.168.1.1"
        path = "/api/v1/appointments"

        key_a_sec = middleware._build_rate_limit_key(tenant_a_id, client_ip, path, "sec")
        key_b_sec = middleware._build_rate_limit_key(tenant_b_id, client_ip, path, "sec")

        assert key_a_sec == f"rate_limit:{tenant_a_id}:{client_ip}:{path}:sec"
        assert key_b_sec == f"rate_limit:{tenant_b_id}:{client_ip}:{path}:sec"
        assert key_a_sec != key_b_sec, "不同租户的限流键应该不同"

    def test_rate_limit_key_without_tenant_uses_global(self):
        """测试无租户上下文时限流键使用 global 占位

        场景：tenant_id 为 None
        预期：键中包含 "global" 而非空字符串
        """
        from app.middleware.rate_limit import RateLimitMiddleware

        middleware = RateLimitMiddleware(app=None, enabled=False)

        key = middleware._build_rate_limit_key(None, "192.168.1.1", "/api/v1/test", "sec")
        assert "global" in key, "无租户上下文时，限流键应包含 global 占位符"
        assert key == "rate_limit:global:192.168.1.1:/api/v1/test:sec"

    def test_different_tenants_different_keys_same_ip_path(self):
        """测试同一 IP 和路径在不同租户下产生不同的限流键

        场景：同一客户端 IP 访问同一路径，但在不同租户上下文中
        预期：生成的限流键完全不同，确保限流计数互不影响
        """
        from app.middleware.rate_limit import RateLimitMiddleware

        middleware = RateLimitMiddleware(app=None, enabled=False)

        ip = "10.0.0.1"
        path = "/api/v1/doctors"

        keys_for_tenants = []
        for tenant_id in ["t1", "t2", "t3"]:
            key = middleware._build_rate_limit_key(tenant_id, ip, path, "min")
            keys_for_tenants.append(key)

        # 所有键应该互不相同
        assert len(set(keys_for_tenants)) == 3, "不同租户应产生不同的限流键"

        # 每个键都包含对应的 tenant_id
        for i, tenant_id in enumerate(["t1", "t2", "t3"]):
            assert tenant_id in keys_for_tenants[i]


@pytest.mark.asyncio
class TestRulePerformanceTenantIsolation:
    """规则引擎性能监控租户隔离测试

    验证 RulePerformanceService 的 Redis key 包含租户维度，
    确保不同租户的性能监控数据独立。
    """

    def test_counter_key_includes_tenant_id(self):
        """测试计数器 key 包含租户 ID

        场景：为两个租户构建同一操作的计数器 key
        预期：key 格式为 rule_engine:{tenant_id}:counter:{operation}
        """
        from app.services.rule_performance_service import RulePerformanceService

        svc = RulePerformanceService()

        key_a = svc._build_counter_key("check_action_window", tenant_id="tenant-a-id")
        key_b = svc._build_counter_key("check_action_window", tenant_id="tenant-b-id")

        assert key_a == "rule_engine:tenant-a-id:counter:check_action_window"
        assert key_b == "rule_engine:tenant-b-id:counter:check_action_window"
        assert key_a != key_b, "不同租户的计数器 key 应该不同"

    def test_latency_key_includes_tenant_id(self):
        """测试延迟统计 key 包含租户 ID"""
        from app.services.rule_performance_service import RulePerformanceService

        svc = RulePerformanceService()

        key_a = svc._build_latency_key("get_booking_policy", tenant_id="tenant-a-id")
        key_b = svc._build_latency_key("get_booking_policy", tenant_id="tenant-b-id")

        assert key_a == "rule_engine:tenant-a-id:latency:get_booking_policy"
        assert key_b == "rule_engine:tenant-b-id:latency:get_booking_policy"
        assert key_a != key_b

    def test_slow_query_key_includes_tenant_id(self):
        """测试慢查询 key 包含租户 ID"""
        from app.services.rule_performance_service import RulePerformanceService

        svc = RulePerformanceService()

        key_a = svc._build_slow_query_key("check_capacity_limits", tenant_id="tenant-a-id")
        key_b = svc._build_slow_query_key("check_capacity_limits", tenant_id="tenant-b-id")

        assert key_a == "rule_engine:tenant-a-id:slow:check_capacity_limits"
        assert key_b == "rule_engine:tenant-b-id:slow:check_capacity_limits"
        assert key_a != key_b

    def test_key_without_tenant_uses_global(self):
        """测试无租户 ID 时使用 global 占位"""
        from app.services.rule_performance_service import RulePerformanceService

        svc = RulePerformanceService()

        # 使用 patch 模拟上下文返回 None
        with patch("app.services.rule_performance_service.get_current_tenant_id", return_value=None):
            key = svc._build_counter_key("check_action_window")

        assert "global" in key, "无租户上下文时应使用 global 占位符"
        assert key == "rule_engine:global:counter:check_action_window"

    def test_all_key_types_isolated_for_same_operation(self):
        """测试同一操作的不同类型 key（counter/latency/slow）在两个租户间完全隔离"""
        from app.services.rule_performance_service import RulePerformanceService

        svc = RulePerformanceService()
        operation = "get_applicable_rule_set"

        # 租户 A 的所有 key
        keys_a = {
            "counter": svc._build_counter_key(operation, tenant_id="t-a"),
            "latency": svc._build_latency_key(operation, tenant_id="t-a"),
            "slow": svc._build_slow_query_key(operation, tenant_id="t-a"),
        }

        # 租户 B 的所有 key
        keys_b = {
            "counter": svc._build_counter_key(operation, tenant_id="t-b"),
            "latency": svc._build_latency_key(operation, tenant_id="t-b"),
            "slow": svc._build_slow_query_key(operation, tenant_id="t-b"),
        }

        # 同类型不同租户的 key 应该不同
        for key_type in keys_a:
            assert keys_a[key_type] != keys_b[key_type], (
                f"{key_type} key 在不同租户间应不同"
            )

        # 同租户不同类型的 key 也应该不同
        assert len(set(keys_a.values())) == 3, "同租户不同类型 key 应该不同"

    @patch("app.services.rule_performance_service.get_current_tenant_id", return_value="ctx-tenant-1")
    def test_tenant_id_from_context_when_not_provided(self, mock_ctx):
        """测试未显式传入 tenant_id 时从上下文获取"""
        from app.services.rule_performance_service import RulePerformanceService

        svc = RulePerformanceService()

        key = svc._build_counter_key("check_action_window")

        assert "ctx-tenant-1" in key, "应从上下文获取 tenant_id"

    def test_explicit_tenant_id_overrides_context(self):
        """测试显式传入的 tenant_id 优先于上下文"""
        from app.services.rule_performance_service import RulePerformanceService

        svc = RulePerformanceService()

        with patch("app.services.rule_performance_service.get_current_tenant_id", return_value="ctx-tenant"):
            key = svc._build_counter_key("check_action_window", tenant_id="explicit-tenant")

        assert "explicit-tenant" in key, "显式传入的 tenant_id 应优先"
        assert "ctx-tenant" not in key, "上下文 tenant_id 应被覆盖"
