"""T-6(d)：公开端写入口守卫（require_tenant_active_for_write）测试

该守卫的语义：
- 无租户上下文直接放行（由中间件保证公开端必有上下文，组合语义见 T-3）；
- 租户禁用/欠费/订阅到期 → 403 且带结构化错误码。
"""
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from app.common.tenant_deps import require_tenant_active_for_write
from app.middleware.tenant_context import clear_tenant_context, set_tenant_context

pytestmark = [pytest.mark.security]


async def test_guard_passes_without_tenant_context(db_session):
    """无租户上下文时守卫放行（不在本层兜底，由中间件负责）"""
    clear_tenant_context()
    result = await require_tenant_active_for_write(db_session)
    assert result is None


@pytest.mark.parametrize(
    ("tenant_status", "expected_code"),
    [
        (0, "TENANT_DISABLED"),
        (2, "TENANT_SUSPENDED_WRITE"),
    ],
)
async def test_guard_blocks_disabled_or_overdue_tenant(
    db_session, multi_tenant_env, tenant_status, expected_code
):
    env = multi_tenant_env
    env.tenant_a.status = tenant_status
    await db_session.commit()

    set_tenant_context(env.tenant_a.id)
    try:
        with pytest.raises(HTTPException) as exc_info:
            await require_tenant_active_for_write(db_session)
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == expected_code
    finally:
        clear_tenant_context()


async def test_guard_blocks_expired_subscription(db_session, multi_tenant_env):
    """status=1 但订阅已过期（定时任务未及转换的窗口期）→ 403"""
    env = multi_tenant_env
    env.tenant_a.status = 1
    env.tenant_a.subscription_end_at = datetime.utcnow() - timedelta(days=1)
    await db_session.commit()

    set_tenant_context(env.tenant_a.id)
    try:
        with pytest.raises(HTTPException) as exc_info:
            await require_tenant_active_for_write(db_session)
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "TENANT_SUSPENDED_WRITE"
    finally:
        clear_tenant_context()


async def test_guard_passes_active_tenant(db_session, multi_tenant_env):
    """正常租户放行（防守卫误伤）"""
    env = multi_tenant_env
    env.tenant_a.status = 1
    env.tenant_a.subscription_end_at = datetime.utcnow() + timedelta(days=30)
    await db_session.commit()

    set_tenant_context(env.tenant_a.id)
    try:
        assert await require_tenant_active_for_write(db_session) is None
    finally:
        clear_tenant_context()
