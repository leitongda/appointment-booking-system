"""P2C-6：资源与消息四模块租户锚点矩阵回归测试

覆盖排班/医生/门店/科室/消息的列表与详情隔离、公开路径灰度校验。
"""
import uuid
from datetime import datetime

import bcrypt
import pytest
import pytest_asyncio

from app.models.department import Department
from app.models.doctor import Doctor
from app.models.message import Message

pytestmark = [pytest.mark.security, pytest.mark.multi_tenant]


def _auth(token: str, tenant_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id
    return headers


async def _create_doctor_for(db_session, tenant_id, store_id, name):
    dept = Department(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        store_id=store_id,
        name=f"{name}科室",
        status=1,
    )
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)

    doctor = Doctor(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        store_id=store_id,
        department_id=dept.id,
        name=name,
        username=f"p2c_{uuid.uuid4().hex[:8]}",
        phone=f"131{uuid.uuid4().int % 10**8:08d}",
        password_hash=bcrypt.hashpw(uuid.uuid4().hex.encode(), bcrypt.gensalt()).decode(),
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return dept, doctor


@pytest_asyncio.fixture
async def p2c_env(db_session, factory, multi_tenant_env):
    env = multi_tenant_env

    env.department_a, env.doctor_a = await _create_doctor_for(
        db_session, env.tenant_a.id, env.store_a.id, "P2C医生A"
    )
    env.department_b, env.doctor_b = await _create_doctor_for(
        db_session, env.tenant_b.id, env.store_b.id, "P2C医生B"
    )

    env.schedule_a = await factory.create_schedule(
        env.tenant_a.id, env.doctor_a.id, env.store_a.id
    )
    env.schedule_b = await factory.create_schedule(
        env.tenant_b.id, env.doctor_b.id, env.store_b.id
    )

    env.message_a = Message(
        id=str(uuid.uuid4()),
        tenant_id=env.tenant_a.id,
        store_id=env.store_a.id,
        user_id=env.admin_a.id,
        user_type="admin",
        title="租户A消息",
        content="A",
        message_type="system",
        is_read=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    env.message_b = Message(
        id=str(uuid.uuid4()),
        tenant_id=env.tenant_b.id,
        store_id=env.store_b.id,
        user_id=env.admin_b.id,
        user_type="admin",
        title="租户B消息",
        content="B",
        message_type="system",
        is_read=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add_all([env.message_a, env.message_b])
    await db_session.commit()
    return env


class TestSchedulesAnchor:
    async def test_list_only_own_tenant(self, async_client, p2c_env, admin_token_factory):
        env = p2c_env
        token = admin_token_factory(env.admin_a)
        response = await async_client.get(
            "/api/v1/schedules", headers=_auth(token, env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = {item["id"] for item in response.json()["data"]}
        assert env.schedule_a.id in ids
        assert env.schedule_b.id not in ids

    async def test_cross_tenant_detail_404(self, async_client, p2c_env, admin_token_factory):
        env = p2c_env
        token = admin_token_factory(env.admin_a)
        response = await async_client.get(
            f"/api/v1/schedules/{env.schedule_b.id}",
            headers=_auth(token, env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

    async def test_platform_admin_without_tenant_400_when_switch_on(
        self, async_client, p2c_env, admin_token_factory, monkeypatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "PATIENT_ANCHOR_FAIL_CLOSE", True)
        env = p2c_env
        token = admin_token_factory(env.platform_admin)
        response = await async_client.get("/api/v1/schedules", headers=_auth(token))
        assert response.status_code == 400, response.text


class TestDoctorsAnchor:
    async def test_list_only_own_tenant(self, async_client, p2c_env, admin_token_factory):
        env = p2c_env
        token = admin_token_factory(env.admin_a)
        response = await async_client.get(
            "/api/v1/doctors", headers=_auth(token, env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = {item["id"] for item in response.json()["data"]}
        assert env.doctor_a.id in ids
        assert env.doctor_b.id not in ids

    async def test_cross_tenant_detail_404(self, async_client, p2c_env, admin_token_factory):
        env = p2c_env
        token = admin_token_factory(env.admin_a)
        response = await async_client.get(
            f"/api/v1/doctors/{env.doctor_b.id}",
            headers=_auth(token, env.tenant_a.id),
        )
        assert response.status_code in (403, 404), response.text


class TestStoresAnchor:
    async def test_list_and_detail_isolation(self, async_client, p2c_env, admin_token_factory):
        env = p2c_env
        token = admin_token_factory(env.admin_a)

        listing = await async_client.get(
            "/api/v1/stores", headers=_auth(token, env.tenant_a.id)
        )
        assert listing.status_code == 200, listing.text
        ids = {item["id"] for item in listing.json()["data"]}
        assert env.store_a.id in ids
        assert env.store_b.id not in ids

        detail = await async_client.get(
            f"/api/v1/stores/{env.store_b.id}",
            headers=_auth(token, env.tenant_a.id),
        )
        assert detail.status_code in (403, 404), detail.text

    async def test_check_unique_ignores_other_tenant(self, async_client, p2c_env, admin_token_factory):
        env = p2c_env
        token = admin_token_factory(env.admin_a)
        response = await async_client.get(
            "/api/v1/stores/check-unique",
            params={"field": "code", "value": env.store_b.code},
            headers=_auth(token, env.tenant_a.id),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        data = body.get("data") or body
        assert data["exists"] is False


class TestDepartmentsAnchor:
    async def test_list_and_detail_isolation(self, async_client, p2c_env, admin_token_factory):
        env = p2c_env
        token = admin_token_factory(env.admin_a)

        listing = await async_client.get(
            "/api/v1/departments/all", headers=_auth(token, env.tenant_a.id)
        )
        assert listing.status_code == 200, listing.text
        ids = {item["id"] for item in listing.json()["data"]}
        assert env.department_a.id in ids
        assert env.department_b.id not in ids

        detail = await async_client.get(
            f"/api/v1/departments/{env.department_b.id}",
            headers=_auth(token, env.tenant_a.id),
        )
        assert detail.status_code in (403, 404), detail.text


class TestMessagesAnchor:
    async def test_list_only_own_tenant(self, async_client, p2c_env, admin_token_factory):
        env = p2c_env
        token = admin_token_factory(env.admin_a)
        response = await async_client.get(
            "/api/v1/messages", headers=_auth(token, env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        body = response.json()
        ids = {item["id"] for item in body["data"]}
        assert env.message_a.id in ids
        assert env.message_b.id not in ids
        # total 必须收敛到本租户（1 条），不得聚合到 B
        assert body.get("total") == 1, response.text


class TestPublicScheduleGuard:
    async def test_available_requires_context_when_configured(
        self, async_client, p2c_env, monkeypatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(
            settings, "PUBLIC_TENANT_REQUIRED_EXTRA_PATHS", ["/api/v1/schedules/available"]
        )
        env = p2c_env
        response = await async_client.get(
            f"/api/v1/schedules/available/{env.doctor_a.id}"
        )
        assert response.status_code == 400, response.text
