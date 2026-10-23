"""T-3 fail-close 行为测试

核心不变量：非平台管理员缺少租户归属时必须被拒（403），而不是返回全量数据；
平台管理员是唯一例外；公开端路径缺少租户上下文返回 400。
"""
import json
import uuid
from datetime import datetime

import pytest
from fastapi import HTTPException

from app.common.tenant_deps import get_tenant_filter
from app.middleware.tenant_context import clear_tenant_context
from app.models.admin import Admin, Role

pytestmark = [pytest.mark.security, pytest.mark.multi_tenant]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_admin_without_tenant(db_session) -> Admin:
    """构造非平台、未关联租户的管理员（异常数据，用于 fail-close 断言）"""
    role = Role(
        id=str(uuid.uuid4()),
        name="审计员",
        code=f"AUDITOR_{uuid.uuid4().hex[:8].upper()}",
        tenant_id=None,
        status=1,
        permissions=json.dumps([]),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)

    admin = Admin(
        id=str(uuid.uuid4()),
        username=f"unbound_{uuid.uuid4().hex[:8]}",
        password_hash="not-used",
        name="未绑定租户管理员",
        role_id=role.id,
        tenant_id=None,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


async def test_unbound_admin_is_rejected_by_tenant_anchored_endpoint(
    async_client, db_session, admin_token_factory
):
    """以 admin.tenant_id 为锚的接口对无租户管理员必须 403（audit-logs 导出）"""
    admin = await _create_admin_without_tenant(db_session)
    token = admin_token_factory(admin)

    response = await async_client.get(
        "/api/v1/audit-logs/export", headers=_auth(token)
    )
    assert response.status_code == 403, response.text


def test_tenant_filter_fails_closed_when_switch_enabled(monkeypatch):
    """TENANT_FILTER_FAIL_CLOSE 开启时，非平台管理员缺 tenant_id 直接 403"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "TENANT_FILTER_FAIL_CLOSE", True)

    with pytest.raises(HTTPException) as exc_info:
        get_tenant_filter(
            {
                "id": "admin-x",
                "tenant_id": None,
                "is_super_admin": False,
                "is_platform_admin": False,
            }
        )
    assert exc_info.value.status_code == 403


def test_platform_admins_keep_cross_tenant_view(monkeypatch):
    """平台管理员（super / platform）是唯一例外，切开关也不受影响"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "TENANT_FILTER_FAIL_CLOSE", True)
    assert get_tenant_filter({"is_super_admin": True, "tenant_id": None}) is None
    assert get_tenant_filter({"is_platform_admin": True, "tenant_id": None}) is None


async def test_platform_admin_sees_all_tenants_roles(
    async_client, multi_tenant_env, admin_token_factory
):
    """平台管理员跨租户查询可见全量（正向例外路径，防误伤）"""
    token = admin_token_factory(multi_tenant_env.platform_admin)
    response = await async_client.get("/api/v1/admin/roles", headers=_auth(token))
    assert response.status_code == 200, response.text
    ids = {item["id"] for item in response.json()["data"]}
    assert multi_tenant_env.role_a.id in ids
    assert multi_tenant_env.role_b.id in ids


async def test_tenant_admin_only_sees_own_roles(
    async_client, multi_tenant_env, admin_token_factory
):
    """租户管理员只看到本租户角色，看不到其他租户角色"""
    token = admin_token_factory(multi_tenant_env.admin_a)
    response = await async_client.get("/api/v1/admin/roles", headers=_auth(token))
    assert response.status_code == 200, response.text
    ids = {item["id"] for item in response.json()["data"]}
    assert multi_tenant_env.role_a.id in ids
    assert multi_tenant_env.role_b.id not in ids


async def test_cross_tenant_role_detail_returns_404(
    async_client, multi_tenant_env, admin_token_factory
):
    """租户管理员按 id 访问其他租户角色 → 404（服务层租户过滤）"""
    token = admin_token_factory(multi_tenant_env.admin_a)
    response = await async_client.get(
        f"/api/v1/admin/roles/{multi_tenant_env.role_b.id}", headers=_auth(token)
    )
    assert response.status_code == 404, response.text


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/doctors/recommended",
        "/api/v1/doctors/public",
        "/api/v1/stores/by-code?code=NOT_EXIST",
    ],
)
async def test_public_paths_require_tenant_context(async_client, path):
    """公开端必需路径缺少任何租户头 → 400，而非 200 全量"""
    clear_tenant_context()
    response = await async_client.get(path)
    assert response.status_code == 400, response.text


async def test_unbound_admin_roles_403_when_fail_close_enabled(
    async_client, db_session, admin_token_factory, monkeypatch
):
    """P1-3 API 级：开关开启后，无租户管理员访问角色列表 → 403"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "TENANT_FILTER_FAIL_CLOSE", True)
    admin = await _create_admin_without_tenant(db_session)
    token = admin_token_factory(admin)

    response = await async_client.get("/api/v1/admin/roles", headers=_auth(token))
    assert response.status_code == 403, response.text


async def test_tenant_code_header_mismatch_is_rejected(
    async_client, multi_tenant_env, admin_token_factory, monkeypatch
):
    """P1-4：只带 X-Tenant-Code 且指向他租户 → 403（换 code 头绕过应被拒）"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "TENANT_CONSISTENCY_FAIL_CLOSE", True)
    env = multi_tenant_env
    token = admin_token_factory(env.admin_a)

    response = await async_client.get(
        "/api/v1/admin/roles",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-Code": env.tenant_b.tenant_code,
        },
    )
    assert response.status_code == 403, response.text


async def test_tenant_code_header_match_is_allowed(
    async_client, multi_tenant_env, admin_token_factory, monkeypatch
):
    """P1-4：code 头与账号租户一致时正常放行"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "TENANT_CONSISTENCY_FAIL_CLOSE", True)
    env = multi_tenant_env
    token = admin_token_factory(env.admin_a)

    response = await async_client.get(
        "/api/v1/admin/roles",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-Code": env.tenant_a.tenant_code,
        },
    )
    assert response.status_code == 200, response.text
