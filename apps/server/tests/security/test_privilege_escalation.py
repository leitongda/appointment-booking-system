"""提权链负向测试

覆盖两条自我提权路径：
1. 租户管理员创建 code="SUPER_ADMIN" 或 permissions=["*"] 的角色；
2. 租户管理员创建/更新管理员时指派平台或其他租户的角色。

P1-2 已落地：保留字黑名单、role_id 租户归属校验、载荷 tenant_id 换锚防护。
"""
import uuid

import pytest

pytestmark = [pytest.mark.security]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_tenant_admin_cannot_create_super_admin_role(
    async_client, multi_tenant_env, admin_token_factory
):
    """租户管理员创建 code=SUPER_ADMIN 的角色应被拒（保留字黑名单）"""
    token = admin_token_factory(multi_tenant_env.admin_a)
    response = await async_client.post(
        "/api/v1/admin/roles",
        headers=_auth(token),
        json={
            "name": "越权超管",
            "code": "SUPER_ADMIN",
            "permissions": ["*"],
        },
    )
    assert 400 <= response.status_code < 500, response.text


async def test_tenant_admin_cannot_create_wildcard_permission_role(
    async_client, multi_tenant_env, admin_token_factory
):
    """租户管理员创建 permissions=["*"] 的自定义角色应被拒"""
    token = admin_token_factory(multi_tenant_env.admin_a)
    response = await async_client.post(
        "/api/v1/admin/roles",
        headers=_auth(token),
        json={
            "name": "全权限角色",
            "code": f"ALL_POWER_{uuid.uuid4().hex[:8].upper()}",
            "permissions": ["*"],
        },
    )
    assert 400 <= response.status_code < 500, response.text


async def test_tenant_admin_cannot_assign_platform_role(
    async_client, multi_tenant_env, admin_token_factory
):
    """租户管理员创建管理员时指派平台角色 role_id 应被拒（租户归属校验）"""
    token = admin_token_factory(multi_tenant_env.admin_a)
    response = await async_client.post(
        "/api/v1/admin/admins",
        headers=_auth(token),
        json={
            "username": f"escalated_{uuid.uuid4().hex[:8]}",
            "name": "提权账号",
            "role_id": multi_tenant_env.platform_admin.role_id,
        },
    )
    assert 400 <= response.status_code < 500, response.text


async def test_tenant_admin_cannot_run_cross_tenant_migration(
    async_client, multi_tenant_env, admin_token_factory
):
    """迁移端点仅限平台管理员（既有守卫，现状即应 403）"""
    token = admin_token_factory(multi_tenant_env.admin_a)
    response = await async_client.post(
        f"/api/v1/tenants/{multi_tenant_env.tenant_b.id}/migrate/precheck",
        headers=_auth(token),
        json={
            "source_tenant_id": multi_tenant_env.tenant_a.id,
            "entity_types": ["stores"],
        },
    )
    assert response.status_code == 403, response.text

    response = await async_client.post(
        f"/api/v1/tenants/{multi_tenant_env.tenant_b.id}/migrate",
        headers=_auth(token),
        json={
            "source_tenant_id": multi_tenant_env.tenant_a.id,
            "entity_types": ["stores"],
        },
    )
    assert response.status_code == 403, response.text


async def test_platform_admin_can_create_role(
    async_client, multi_tenant_env, admin_token_factory
):
    """平台管理员执行同样操作应成功（防止守卫收紧误伤平台管理员）"""
    token = admin_token_factory(multi_tenant_env.platform_admin)
    response = await async_client.post(
        "/api/v1/admin/roles",
        headers=_auth(token),
        json={
            "name": "平台自定义角色",
            "code": f"PLATFORM_CUSTOM_{uuid.uuid4().hex[:8].upper()}",
            "permissions": [],
        },
    )
    assert response.status_code < 400, response.text


async def test_tenant_admin_cannot_rename_role_to_reserved_code(
    async_client, multi_tenant_env, admin_token_factory
):
    """租户管理员不能把自建角色改名为保留编码"""
    token = admin_token_factory(multi_tenant_env.admin_a)
    created = await async_client.post(
        "/api/v1/admin/roles",
        headers=_auth(token),
        json={
            "name": "普通角色",
            "code": f"CUSTOM_{uuid.uuid4().hex[:8].upper()}",
            "permissions": [],
        },
    )
    assert created.status_code < 400, created.text
    role_id = created.json()["data"]["id"]

    response = await async_client.put(
        f"/api/v1/admin/roles/{role_id}",
        headers=_auth(token),
        json={"code": "PLATFORM_ADMIN"},
    )
    # 改名接口若拒绝则 4xx；若载荷被忽略也必须保持原编码（两条路径都不得提权）
    assert response.status_code < 500, response.text
    detail = await async_client.get(
        f"/api/v1/admin/roles/{role_id}", headers=_auth(token)
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["data"]["code"] != "PLATFORM_ADMIN"


async def test_tenant_admin_cannot_switch_tenant_via_payload(
    async_client, multi_tenant_env, admin_token_factory
):
    """载荷 tenant_id 不能改变建号锚点（禁止跨租户建号）"""
    token = admin_token_factory(multi_tenant_env.admin_a)
    response = await async_client.post(
        "/api/v1/admin/admins",
        headers=_auth(token),
        json={
            "username": f"cross_tenant_{uuid.uuid4().hex[:8]}",
            "tenant_id": multi_tenant_env.tenant_b.id,
        },
    )
    assert response.status_code == 403, response.text


async def test_platform_admin_must_specify_tenant_when_creating_admin(
    async_client, multi_tenant_env, admin_token_factory
):
    """平台管理员不带 tenant_id 建号应 400（必须显式指定目标租户）"""
    token = admin_token_factory(multi_tenant_env.platform_admin)
    response = await async_client.post(
        "/api/v1/admin/admins",
        headers=_auth(token),
        json={"username": f"no_tenant_{uuid.uuid4().hex[:8]}"},
    )
    assert response.status_code == 400, response.text


async def test_platform_admin_can_create_admin_for_tenant(
    async_client, multi_tenant_env, admin_token_factory
):
    """平台管理员显式指定 tenant_id 后可以建号（正常路径不受影响）"""
    token = admin_token_factory(multi_tenant_env.platform_admin)
    response = await async_client.post(
        "/api/v1/admin/admins",
        headers=_auth(token),
        json={
            "username": f"platform_created_{uuid.uuid4().hex[:8]}",
            "tenant_id": multi_tenant_env.tenant_a.id,
            "role_id": multi_tenant_env.role_a.id,
        },
    )
    assert response.status_code < 400, response.text


async def test_tenant_admin_cannot_assign_other_tenant_role_on_update(
    async_client, multi_tenant_env, admin_token_factory
):
    """更新本租户成员时不得指派其他租户的角色"""
    token = admin_token_factory(multi_tenant_env.admin_a)
    response = await async_client.put(
        f"/api/v1/admin/admins/{multi_tenant_env.admin_a.id}",
        headers=_auth(token),
        json={"role_id": multi_tenant_env.role_b.id},
    )
    assert 400 <= response.status_code < 500, response.text


async def test_tenant_admin_can_assign_own_tenant_role_on_update(
    async_client, multi_tenant_env, admin_token_factory
):
    """更新本租户成员时指派本租户角色正常通过"""
    token = admin_token_factory(multi_tenant_env.admin_a)
    response = await async_client.put(
        f"/api/v1/admin/admins/{multi_tenant_env.admin_a.id}",
        headers=_auth(token),
        json={"role_id": multi_tenant_env.role_a.id},
    )
    assert response.status_code < 400, response.text
