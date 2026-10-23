"""T-6(a)：租户停服时管理员登录拦截测试"""
import uuid
from datetime import datetime, timedelta

import bcrypt
import pytest

from app.middleware.tenant_context import clear_tenant_context
from app.models.admin import Admin

pytestmark = [pytest.mark.security]


def _random_password() -> str:
    """每次生成一次性密码，避免在测试源码中出现固定凭据"""
    return uuid.uuid4().hex


async def _login(async_client, username: str, password: str):
    return await async_client.post(
        "/api/v1/admin/login",
        json={"username": username, "password": password, "encrypted": False},
    )


async def _load_admin(db_session, admin_id: str) -> Admin:
    """按主键取管理员并加载角色/租户关系（避免在测试中拼接查询）"""
    admin = await db_session.get(Admin, admin_id)
    await db_session.refresh(admin, ["role", "tenant"])
    return admin


@pytest.mark.parametrize("tenant_status", [0, 2])
async def test_admin_login_blocked_when_tenant_suspended(
    async_client, db_session, multi_tenant_env, tenant_status
):
    env = multi_tenant_env
    password = _random_password()
    env.admin_a.password_hash = bcrypt.hashpw(
        password.encode(), bcrypt.gensalt()
    ).decode()
    env.tenant_a.status = tenant_status
    await db_session.commit()

    response = await _login(async_client, env.admin_a.username, password)
    assert response.status_code == 403, response.text


async def test_admin_login_succeeds_for_active_tenant(
    async_client, db_session, multi_tenant_env
):
    env = multi_tenant_env
    password = _random_password()
    env.admin_a.password_hash = bcrypt.hashpw(
        password.encode(), bcrypt.gensalt()
    ).decode()
    env.tenant_a.status = 1
    await db_session.commit()

    response = await _login(async_client, env.admin_a.username, password)
    assert response.status_code == 200, response.text


async def test_login_helper_blocks_trial_expired(db_session, multi_tenant_env):
    """试用期到期（status=3 + 订阅过期）由登录辅助函数拦截"""
    from fastapi import HTTPException

    from app.modules.admin.router_auth_login import _check_tenant_status_for_login

    env = multi_tenant_env
    env.tenant_a.status = 3
    env.tenant_a.subscription_end_at = datetime.utcnow() - timedelta(days=1)
    await db_session.commit()

    admin = await _load_admin(db_session, env.admin_a.id)

    with pytest.raises(HTTPException) as exc_info:
        _check_tenant_status_for_login(admin)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error_code"] == "TENANT_TRIAL_EXPIRED"


async def test_login_helper_allows_active_tenant(db_session, multi_tenant_env):
    from app.modules.admin.router_auth_login import _check_tenant_status_for_login

    env = multi_tenant_env
    env.tenant_a.status = 1
    env.tenant_a.subscription_end_at = None
    await db_session.commit()

    admin = await _load_admin(db_session, env.admin_a.id)
    _check_tenant_status_for_login(admin)  # 不应抛异常
    clear_tenant_context()
