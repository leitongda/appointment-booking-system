"""管理端读端点权限收口（system:*:list）

2026-10-24 权限收口后的行为契约：
- `GET /admins`、`/admins/{id}` 挂 `require_permission("system:user:list", "system:user")`；
- `GET /roles`、`/roles/all`、`/roles/{id}` 挂 `require_permission("system:role:list", "system:role")`；
- OR 父码兼容存量授权：仅有 `system:user`（无细码）的角色仍可访问用户管理读端点；
- 无任何 system 码的受限角色在这些端点上一律 403。
"""
import json
from datetime import datetime
from uuid import uuid4

import pytest
import pytest_asyncio

from app.models.admin import Admin, Role

pytestmark = [pytest.mark.security, pytest.mark.multi_tenant]

ADMINS = "/api/v1/admin/admins"
ADMINS_ALL = "/api/v1/admin/admins/all"
ROLES = "/api/v1/admin/roles"
ROLES_ALL = "/api/v1/admin/roles/all"


@pytest_asyncio.fixture
async def read_guard_env(db_session, multi_tenant_env):
    """在租户 A 里追加三个不同权限面的管理员。"""
    env = multi_tenant_env

    def _role(code: str, permissions: list[str]) -> Role:
        return Role(
            id=str(uuid4()),
            tenant_id=env.tenant_a.id,
            name=f"角色-{code}",
            code=code,
            status=1,
            permissions=json.dumps(permissions),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def _admin(username: str, role: Role) -> Admin:
        return Admin(
            id=str(uuid4()),
            tenant_id=env.tenant_a.id,
            username=username,
            password_hash="x",
            name=username,
            role_id=role.id,
            current_store_id=env.store_a.id,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    role_limited = _role(f"RG_LIMIT_{uuid4().hex[:6]}", ["patient:list"])
    role_parent = _role(f"RG_PARENT_{uuid4().hex[:6]}", ["system:user"])
    role_fine = _role(
        f"RG_FINE_{uuid4().hex[:6]}", ["system:user:list", "system:role:list"]
    )
    db_session.add_all([role_limited, role_parent, role_fine])
    await db_session.flush()

    admin_limited = _admin(f"rg_limit_{uuid4().hex[:6]}", role_limited)
    admin_parent = _admin(f"rg_parent_{uuid4().hex[:6]}", role_parent)
    admin_fine = _admin(f"rg_fine_{uuid4().hex[:6]}", role_fine)
    db_session.add_all([admin_limited, admin_parent, admin_fine])
    await db_session.commit()

    env.admin_limited = admin_limited
    env.admin_parent = admin_parent
    env.admin_fine = admin_fine
    return env


def _headers(token: str, tenant_id: str) -> dict:
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}


class TestAdminsReadPermission:
    async def test_limited_role_is_rejected(
        self, async_client, read_guard_env, admin_token_factory
    ):
        env = read_guard_env
        response = await async_client.get(
            ADMINS, headers=_headers(admin_token_factory(env.admin_limited), env.tenant_a.id)
        )
        assert response.status_code == 403, response.text

    async def test_parent_code_grants_backward_compatible_access(
        self, async_client, read_guard_env, admin_token_factory
    ):
        """仅有 system:user 父码（无细码）的存量授权不被锁死。"""
        env = read_guard_env
        response = await async_client.get(
            ADMINS, headers=_headers(admin_token_factory(env.admin_parent), env.tenant_a.id)
        )
        assert response.status_code == 200, response.text

    async def test_parent_code_of_other_module_is_rejected(
        self, async_client, read_guard_env, admin_token_factory
    ):
        """system:user 不能打开 roles 端点（权限码不跨模块）。"""
        env = read_guard_env
        response = await async_client.get(
            ROLES, headers=_headers(admin_token_factory(env.admin_parent), env.tenant_a.id)
        )
        assert response.status_code == 403, response.text

    async def test_fine_grain_code_grants_access(
        self, async_client, read_guard_env, admin_token_factory
    ):
        env = read_guard_env
        for path in (ADMINS, ROLES, ROLES_ALL):
            response = await async_client.get(
                path, headers=_headers(admin_token_factory(env.admin_fine), env.tenant_a.id)
            )
            assert response.status_code == 200, f"{path}: {response.text}"

    async def test_wildcard_admin_unchanged(
        self, async_client, read_guard_env, admin_token_factory
    ):
        """通配权限（*）的租户管理员不受影响（multi_tenant_env 的 admin_a）。"""
        env = read_guard_env
        for path in (ADMINS, ROLES, ROLES_ALL):
            response = await async_client.get(
                path, headers=_headers(admin_token_factory(env.admin_a), env.tenant_a.id)
            )
            assert response.status_code == 200, f"{path}: {response.text}"

    async def test_admin_detail_rejects_limited_role(
        self, async_client, read_guard_env, admin_token_factory
    ):
        env = read_guard_env
        response = await async_client.get(
            f"{ADMINS}/{env.admin_fine.id}",
            headers=_headers(admin_token_factory(env.admin_limited), env.tenant_a.id),
        )
        assert response.status_code == 403, response.text

    async def test_role_detail_rejects_limited_role(
        self, async_client, read_guard_env, admin_token_factory
    ):
        env = read_guard_env
        response = await async_client.get(
            f"{ROLES}/{env.role_a.id}",
            headers=_headers(admin_token_factory(env.admin_limited), env.tenant_a.id),
        )
        assert response.status_code == 403, response.text
