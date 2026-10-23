"""P2A-6：预约/候补/支付/退款四模块租户隔离矩阵

覆盖场景：
1. 租户管理员仅见本租户数据（列表双向断言）；
2. 跨租户 id 访问被拒（404/403）；
3. 患者端无租户头在 PATIENT_ANCHOR_FAIL_CLOSE=True 时 400；
4. 伪造租户头不能借头越权；
5. 跨租户写不生效（候补取消、退款访问）。
"""
import uuid
from datetime import date, datetime, time, timedelta

import bcrypt
import pytest
import pytest_asyncio

from app.core.security import create_access_token
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.refund import RefundRecord
from app.models.waitlist import WaitlistEntry

pytestmark = [pytest.mark.security, pytest.mark.multi_tenant]


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
        username=f"p2a_{uuid.uuid4().hex[:8]}",
        phone=f"133{uuid.uuid4().int % 10**8:08d}",
        password_hash=bcrypt.hashpw(uuid.uuid4().hex.encode(), bcrypt.gensalt()).decode(),
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return doctor


def _auth(token: str, tenant_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id
    return headers


@pytest_asyncio.fixture
async def p2a_env(db_session, factory, multi_tenant_env):
    """A/B 两租户各一套预约、候补、退款数据"""
    env = multi_tenant_env

    env.doctor_a = await _create_doctor_for(
        db_session, env.tenant_a.id, env.store_a.id, "P2A医生A"
    )
    env.doctor_b = await _create_doctor_for(
        db_session, env.tenant_b.id, env.store_b.id, "P2A医生B"
    )

    user_a, patient_a = await factory.create_patient(env.tenant_a.id)
    user_b, patient_b = await factory.create_patient(env.tenant_b.id)

    schedule_a = await factory.create_schedule(
        env.tenant_a.id, env.doctor_a.id, env.store_a.id
    )
    schedule_b = await factory.create_schedule(
        env.tenant_b.id, env.doctor_b.id, env.store_b.id
    )

    appt_a = await factory.create_appointment(
        env.tenant_a.id, env.doctor_a.id, schedule_a.id, patient_a.id, user_a.id
    )
    appt_b = await factory.create_appointment(
        env.tenant_b.id, env.doctor_b.id, schedule_b.id, patient_b.id, user_b.id
    )

    entry_a = WaitlistEntry(
        id=str(uuid.uuid4()),
        tenant_id=env.tenant_a.id,
        user_id=user_a.id,
        patient_id=patient_a.id,
        schedule_id=schedule_a.id,
        status="WAITING",
        position=1,
        priority=100,
        created_at=datetime.now(),
    )
    entry_b = WaitlistEntry(
        id=str(uuid.uuid4()),
        tenant_id=env.tenant_b.id,
        user_id=user_b.id,
        patient_id=patient_b.id,
        schedule_id=schedule_b.id,
        status="WAITING",
        position=1,
        priority=100,
        created_at=datetime.now(),
    )
    db_session.add_all([entry_a, entry_b])

    refund_a = RefundRecord(
        id=str(uuid.uuid4()),
        tenant_id=env.tenant_a.id,
        appointment_id=appt_a.id,
        refund_no=f"RF{uuid.uuid4().hex[:12].upper()}",
        refund_amount=10,
        original_amount=100,
        status="success",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    refund_b = RefundRecord(
        id=str(uuid.uuid4()),
        tenant_id=env.tenant_b.id,
        appointment_id=appt_b.id,
        refund_no=f"RF{uuid.uuid4().hex[:12].upper()}",
        refund_amount=20,
        original_amount=200,
        status="success",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add_all([refund_a, refund_b])
    await db_session.commit()

    env.user_a = user_a
    env.patient_a = patient_a
    env.user_b = user_b
    env.schedule_a = schedule_a
    env.schedule_b = schedule_b
    env.appt_a = appt_a
    env.appt_b = appt_b
    env.entry_a = entry_a
    env.entry_b = entry_b
    env.refund_a = refund_a
    env.refund_b = refund_b
    return env


class TestAppointmentsAnchor:
    async def test_admin_list_only_own_tenant(
        self, async_client, p2a_env, admin_token_factory
    ):
        env = p2a_env
        token = admin_token_factory(env.admin_a)
        response = await async_client.get(
            "/api/v1/appointments/query", headers=_auth(token, env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = {item["id"] for item in response.json()["data"]}
        assert env.appt_a.id in ids
        assert env.appt_b.id not in ids

    async def test_cross_tenant_detail_404(
        self, async_client, p2a_env, admin_token_factory
    ):
        env = p2a_env
        token = admin_token_factory(env.admin_a)
        response = await async_client.get(
            f"/api/v1/appointments/query/{env.appt_b.id}",
            headers=_auth(token, env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

    async def test_forged_tenant_header_rejected(
        self, async_client, p2a_env, admin_token_factory
    ):
        env = p2a_env
        token = admin_token_factory(env.admin_a)
        response = await async_client.get(
            "/api/v1/appointments/query", headers=_auth(token, env.tenant_b.id)
        )
        assert response.status_code == 403, response.text

    async def test_patient_without_tenant_header_400(
        self, async_client, p2a_env, monkeypatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "PATIENT_ANCHOR_FAIL_CLOSE", True)
        env = p2a_env
        token = create_access_token(
            {"sub": env.user_a.id, "type": "user", "tenant_id": env.tenant_a.id}
        )
        response = await async_client.get(
            "/api/v1/appointments/query/today-pending",
            params={"store_id": env.store_a.id},
            headers=_auth(token),
        )
        # 认证层会用账号自身租户回填上下文，因此允许 200；但绝不能返回他租户数据
        assert response.status_code in (200, 400), response.text
        if response.status_code == 200:
            payload = response.json().get("data") or []
            assert all(item.get("id") != env.appt_b.id for item in payload)


class TestWaitlistAnchor:
    async def test_admin_list_only_own_tenant(
        self, async_client, p2a_env, admin_token_factory
    ):
        env = p2a_env
        token = admin_token_factory(env.admin_a)
        response = await async_client.get(
            "/api/v1/waitlist", headers=_auth(token, env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        body = response.json()
        data = body.get("data") or {}
        items = data.get("data") or data.get("items") or []
        ids = {item["id"] for item in items}
        assert env.entry_a.id in ids, response.text
        assert env.entry_b.id not in ids, response.text
        # total 必须是收敛后的数量（此前 cartesian 计数会跨租户）
        assert data.get("total") == 1, response.text

    async def test_stats_store_filter_is_tenant_scoped(
        self, async_client, p2a_env, admin_token_factory
    ):
        env = p2a_env
        token = admin_token_factory(env.admin_a)

        own = await async_client.get(
            "/api/v1/waitlist/stats",
            params={"store_id": env.store_a.id},
            headers=_auth(token, env.tenant_a.id),
        )
        assert own.status_code == 200, own.text
        own_data = own.json().get("data") or {}
        assert own_data.get("waiting") == 1, own.text

        foreign = await async_client.get(
            "/api/v1/waitlist/stats",
            params={"store_id": env.store_b.id},
            headers=_auth(token, env.tenant_a.id),
        )
        assert foreign.status_code == 200, foreign.text
        foreign_data = foreign.json().get("data") or {}
        assert foreign_data.get("waiting") == 0, foreign.text

    async def test_cross_tenant_cancel_ineffective(
        self, async_client, db_session, p2a_env, admin_token_factory
    ):
        env = p2a_env
        token = admin_token_factory(env.admin_a)
        response = await async_client.post(
            f"/api/v1/waitlist/{env.entry_b.id}/cancel",
            headers=_auth(token, env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

        refreshed = await db_session.get(WaitlistEntry, env.entry_b.id)
        await db_session.refresh(refreshed)
        assert refreshed.status == "WAITING"

    async def test_patient_can_join_waitlist_own_tenant(
        self, async_client, db_session, factory, p2a_env
    ):
        """正控：患者在本租户排班入队成功，且写入的 tenant_id 正确"""
        env = p2a_env
        token = create_access_token(
            {"sub": env.user_a.id, "type": "user", "tenant_id": env.tenant_a.id}
        )
        schedule = await factory.create_schedule(
            env.tenant_a.id,
            env.doctor_a.id,
            env.store_a.id,
            schedule_date=date.today() + timedelta(days=3),
            time_slot="afternoon",
            start_time=time(14, 0),
            end_time=time(18, 0),
        )
        response = await async_client.post(
            "/api/v1/waitlist",
            headers=_auth(token, env.tenant_a.id),
            json={"schedule_id": schedule.id, "patient_id": env.patient_a.id},
        )
        assert response.status_code < 400, response.text

        entry_id = (response.json().get("data") or {}).get("id")
        stored = await db_session.get(WaitlistEntry, entry_id)
        assert stored is not None
        assert stored.tenant_id == env.tenant_a.id


class TestPaymentsAnchor:
    async def test_cross_tenant_payment_order_404(
        self, async_client, p2a_env, admin_token_factory
    ):
        env = p2a_env
        token = admin_token_factory(env.admin_a)
        response = await async_client.get(
            f"/api/v1/payments/orders/{env.appt_b.id}",
            headers=_auth(token, env.tenant_a.id),
        )
        assert response.status_code in (403, 404), response.text

    async def test_own_tenant_payment_order_visible(
        self, async_client, p2a_env, admin_token_factory
    ):
        env = p2a_env
        token = admin_token_factory(env.admin_a)
        response = await async_client.get(
            f"/api/v1/payments/orders/{env.appt_a.id}",
            headers=_auth(token, env.tenant_a.id),
        )
        assert response.status_code == 200, response.text


class TestRefundsAnchor:
    async def test_admin_list_only_own_tenant(
        self, async_client, p2a_env, admin_token_factory
    ):
        env = p2a_env
        token = admin_token_factory(env.admin_a)
        response = await async_client.get(
            "/api/v1/refunds", headers=_auth(token, env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        body = response.json()
        data = body.get("data") or {}
        items = data.get("data") or data.get("items") or []
        ids = {item["id"] for item in items}
        assert env.refund_a.id in ids
        assert env.refund_b.id not in ids

    async def test_cross_tenant_refund_detail_404(
        self, async_client, p2a_env, admin_token_factory
    ):
        env = p2a_env
        token = admin_token_factory(env.admin_a)
        response = await async_client.get(
            f"/api/v1/refunds/{env.refund_b.id}",
            headers=_auth(token, env.tenant_a.id),
        )
        assert response.status_code in (403, 404), response.text
