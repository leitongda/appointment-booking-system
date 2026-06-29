"""
限流中间件豁免路径测试

守护 P1-1 修复：高频埋点接口必须被全局限流豁免，由路由自身 IP 限流兜底。
重点验证 session-events/batch 已加入豁免（此前遗漏导致生产开启 rrweb 后被限流）。
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request

from app.middleware.rate_limit import RateLimitMiddleware


def _make_request(path: str) -> Request:
    """构造一个指向给定 path 的 ASGI Request"""
    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "url": {"path": path},
    }
    # 用简化的 Request 构造；dispatch 只用到 request.url.path
    request = MagicMock(spec=Request)
    request.url = MagicMock()
    request.url.path = path
    return request


@pytest.mark.parametrize(
    "path, should_be_excluded, desc",
    [
        # 必须被豁免的埋点接口（高频，由路由内 IP 限流兜底）
        ("/api/v1/analytics/track", True, "analytics/track 应豁免"),
        ("/api/v1/analytics/batch", True, "analytics/batch 应豁免"),
        ("/api/v1/session-events/batch", True, "session-events/batch 应豁免（P1-1 修复）"),
        # 不应被豁免的普通业务路径（仍走全局限流）
        ("/api/v1/appointments", False, "普通业务路径不应豁免"),
        ("/api/v1/users", False, "普通业务路径不应豁免"),
        # 前缀豁免
        ("/health", True, "/health 前缀豁免"),
        ("/docs", True, "/docs 前缀豁免"),
        # 边界：相似但非精确路径不应误豁免
        ("/api/v1/analytics/batch/extra", False, "精确路径的子路径不应被 EXACT 豁免"),
        ("/api/v1/session-events/batchX", False, "前缀相同但非精确路径不应豁免"),
    ],
)
def test_exclude_paths_coverage(path, should_be_excluded, desc):
    """EXCLUDE_EXACT_PATHS 必须精确覆盖三个埋点接口。"""
    exact_excluded = path in RateLimitMiddleware.EXCLUDE_EXACT_PATHS
    prefix_excluded = any(path.startswith(p) for p in RateLimitMiddleware.EXCLUDE_PATHS)
    excluded = exact_excluded or prefix_excluded
    assert excluded == should_be_excluded, f"用例失败：{desc}（path={path}）"


def test_session_events_batch_is_in_exclude_exact():
    """专项断言：session-events/batch 必须在精确豁免列表（回归守护 P1-1）。"""
    assert "/api/v1/session-events/batch" in RateLimitMiddleware.EXCLUDE_EXACT_PATHS


@pytest.mark.asyncio
async def test_dispatch_short_circuits_for_excluded_path():
    """豁免路径不应触发 Redis 限流检查（dispatch 直接放行）。"""
    # 构造一个最小 middleware 实例，用一个 no-op ASGI app
    async def dummy_app(scope, receive, send):
        return None

    middleware = RateLimitMiddleware(dummy_app, enabled=True)

    # mock _get_redis / _check_rate_limit / _get_tenant_limits，验证它们不被调用
    middleware._get_redis = AsyncMock()
    middleware._get_tenant_limits = AsyncMock(return_value=(300, 50))
    middleware._check_rate_limit = AsyncMock(return_value=True)

    request = _make_request("/api/v1/session-events/batch")
    call_next = AsyncMock(return_value=MagicMock())

    await middleware.dispatch(request, call_next)

    # 关键：豁免路径不应查询 Redis / 租户配置
    middleware._get_redis.assert_not_called()
    middleware._get_tenant_limits.assert_not_called()
    middleware._check_rate_limit.assert_not_called()
    # call_next 应被调用（请求放行）
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_dispatch_applies_limit_for_normal_path():
    """非豁免路径应正常触发限流检查（Redis 滑窗）。"""
    async def dummy_app(scope, receive, send):
        return None

    middleware = RateLimitMiddleware(dummy_app, enabled=True)
    middleware._get_redis = AsyncMock(return_value=MagicMock())
    middleware._get_tenant_limits = AsyncMock(return_value=(300, 50))
    middleware._check_rate_limit = AsyncMock(return_value=True)

    # tenant_context 在非豁免路径被调用，mock 掉
    with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=None):
        request = _make_request("/api/v1/appointments")
        request.headers = MagicMock()
        request.headers.get = MagicMock(return_value="")
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        call_next = AsyncMock(return_value=MagicMock())

        await middleware.dispatch(request, call_next)

    # 限流检查应被调用（秒 + 分钟各一次）
    assert middleware._check_rate_limit.call_count == 2
