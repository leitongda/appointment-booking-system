"""p3a8 查询侧租户收口矩阵：诊费 + 门店邮件接收人

覆盖 router 层新增的守卫语义：
- 租户管理员传入他租户 store/doctor/行 ID → 403；
- 本租户资源正常访问（正控，防止「权限 403 冒充租户拦截」）；
- 平台管理员（无显式租户锚点）不受限；
- 此前无鉴权的读端点（types/store-templates/doctors）现在要求登录 → 401。
"""
import uuid
from datetime import datetime

import pytest
import pytest_asyncio

from app.models.doctor import Doctor
from app.models.store_email_recipient import StoreEmailRecipient
from app.core.security import get_password_hash

pytestmark = [pytest.mark.security, pytest.mark.multi_tenant]

TYPES = "/api/v1/consultation-fees/types"
STORE_TEMPLATES = "/api/v1/consultation-fees/store-templates"
DOCTOR_FEES = "/api/v1/consultation-fees/doctors"
RECIPIENTS = "/api/v1/store-email-recipients"


@pytest_asyncio.fixture
async def p3a8_env(db_session, multi_tenant_env):
    from app.models.department import Department

    env = multi_tenant_env

    def _dept(store, label):
        return Department(
            id=str(uuid.uuid4()),
            tenant_id=store.tenant_id,
            store_id=store.id,
            name=f"科室-{label}",
            status=1,
        )

    dept_a = _dept(env.store_a, "P3A8A")
    dept_b = _dept(env.store_b, "P3A8B")
    db_session.add_all([dept_a, dept_b])
    await db_session.flush()

    def _doctor(store, dept, username):
        return Doctor(
            id=str(uuid.uuid4()),
            tenant_id=store.tenant_id,
            store_id=store.id,
            department_id=dept.id,
            name=f"医生-{username}",
            username=username,
            password_hash=get_password_hash("x"),
            status=1,
        )

    env.doctor_a = _doctor(env.store_a, dept_a, f"p3a8a_{uuid.uuid4().hex[:6]}")
    env.doctor_b = _doctor(env.store_b, dept_b, f"p3a8b_{uuid.uuid4().hex[:6]}")

    def _recipient(store, email):
        return StoreEmailRecipient(
            id=str(uuid.uuid4()),
            store_id=store.id,
            tenant_id=store.tenant_id,
            name="接收人",
            email=email,
            event_types='["checkin"]',
            status=1,
        )

    env.recipient_a = _recipient(env.store_a, "a@p3a8.test")
    env.recipient_b = _recipient(env.store_b, "b@p3a8.test")
    db_session.add_all([env.doctor_a, env.doctor_b, env.recipient_a, env.recipient_b])
    await db_session.commit()
    return env


def _h(token: str, tenant_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id
    return headers


class TestConsultationFeesTenantScope:
    async def test_types_list_with_foreign_store_rejected(
        self, async_client, p3a8_env, admin_token_factory
    ):
        env = p3a8_env
        response = await async_client.get(
            TYPES,
            params={"store_id": env.store_b.id},
            headers=_h(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 403, response.text

    async def test_types_list_own_store_ok(
        self, async_client, p3a8_env, admin_token_factory
    ):
        env = p3a8_env
        response = await async_client.get(
            TYPES,
            params={"store_id": env.store_a.id},
            headers=_h(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 200, response.text

    async def test_types_create_with_foreign_store_rejected(
        self, async_client, p3a8_env, admin_token_factory
    ):
        env = p3a8_env
        response = await async_client.post(
            TYPES,
            json={"name": "越权类型", "code": f"xc{uuid.uuid4().hex[:6]}", "store_id": env.store_b.id},
            headers=_h(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 403, response.text

    async def test_store_templates_foreign_store_rejected(
        self, async_client, p3a8_env, admin_token_factory
    ):
        env = p3a8_env
        response = await async_client.get(
            f"{STORE_TEMPLATES}/{env.store_b.id}",
            headers=_h(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 403, response.text

    async def test_doctor_fees_foreign_doctor_rejected(
        self, async_client, p3a8_env, admin_token_factory
    ):
        env = p3a8_env
        for path in (
            f"{DOCTOR_FEES}/{env.doctor_b.id}",
            f"{DOCTOR_FEES}/{env.doctor_b.id}/grouped",
            f"{DOCTOR_FEES}/{env.doctor_b.id}/fees",
        ):
            response = await async_client.get(
                path, headers=_h(admin_token_factory(env.admin_a), env.tenant_a.id)
            )
            assert response.status_code == 403, f"{path}: {response.text}"

    async def test_doctor_fees_own_doctor_ok(
        self, async_client, p3a8_env, admin_token_factory
    ):
        env = p3a8_env
        response = await async_client.get(
            f"{DOCTOR_FEES}/{env.doctor_a.id}",
            headers=_h(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        # 404 = 医生存在（守卫通过）但无配置；403 才是租户拦截
        assert response.status_code == 200, response.text

    async def test_previously_open_reads_now_require_auth(self, async_client, p3a8_env):
        env = p3a8_env
        for path in (TYPES, f"{STORE_TEMPLATES}/{env.store_a.id}", f"{DOCTOR_FEES}/{env.doctor_a.id}"):
            response = await async_client.get(path)
            assert response.status_code == 401, f"{path}: {response.text}"

    async def test_platform_admin_not_restricted(
        self, async_client, p3a8_env, admin_token_factory
    ):
        env = p3a8_env
        response = await async_client.get(
            TYPES,
            params={"store_id": env.store_b.id},
            headers=_h(admin_token_factory(env.platform_admin)),
        )
        assert response.status_code == 200, response.text


class TestStoreEmailRecipientsTenantScope:
    async def test_list_with_foreign_store_rejected(
        self, async_client, p3a8_env, admin_token_factory
    ):
        env = p3a8_env
        response = await async_client.get(
            RECIPIENTS,
            params={"store_id": env.store_b.id},
            headers=_h(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 403, response.text

    async def test_create_with_foreign_store_rejected(
        self, async_client, p3a8_env, admin_token_factory
    ):
        env = p3a8_env
        response = await async_client.post(
            RECIPIENTS,
            json={
                "store_id": env.store_b.id,
                "name": "越权接收人",
                "email": "evil@p3a8.test",
                "event_types": ["checkin"],
            },
            headers=_h(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 403, response.text

    async def test_foreign_recipient_row_access_rejected(
        self, async_client, p3a8_env, admin_token_factory
    ):
        env = p3a8_env
        headers = _h(admin_token_factory(env.admin_a), env.tenant_a.id)
        response = await async_client.get(f"{RECIPIENTS}/{env.recipient_b.id}", headers=headers)
        assert response.status_code == 403, response.text

        response = await async_client.put(
            f"{RECIPIENTS}/{env.recipient_b.id}",
            json={"name": "改名"},
            headers=headers,
        )
        assert response.status_code == 403, response.text

        response = await async_client.delete(f"{RECIPIENTS}/{env.recipient_b.id}", headers=headers)
        assert response.status_code == 403, response.text

    async def test_own_recipient_flow_ok(
        self, async_client, p3a8_env, admin_token_factory
    ):
        env = p3a8_env
        headers = _h(admin_token_factory(env.admin_a), env.tenant_a.id)
        response = await async_client.get(
            f"{RECIPIENTS}/{env.recipient_a.id}", headers=headers
        )
        assert response.status_code == 200, response.text

        response = await async_client.put(
            f"{RECIPIENTS}/{env.recipient_a.id}",
            json={"name": "改名A"},
            headers=headers,
        )
        assert response.status_code == 200, response.text
