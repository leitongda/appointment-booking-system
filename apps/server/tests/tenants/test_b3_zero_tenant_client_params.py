"""B3：零租户与客户端参数（R1-12 / R1-2 / R1-16 / R1-17）

覆盖四组验收：
1. shift_types 列表/详情/创建跨租户隔离与锚点落库；
2. settings 租户维度读写（A 改 B 不变）与平台管理员缺租户 400；
3. notification_logs 不再信任 query 里的 tenant_id（A 传 B → 403，平台缺租户 → 400）；
4. unified_message /send、/send-batch 用锚点覆盖请求体 tenant_id（A 传 B → 403）。
"""
import uuid

import pytest
from sqlalchemy import select

from app.models.settings import SystemSetting
from app.models.shift_type import ShiftType
from app.models.unified_template import UnifiedTemplate

pytestmark = [pytest.mark.security, pytest.mark.multi_tenant]


def _auth(token: str, tenant_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id
    return headers


async def _create_shift_type(db_session, tenant_id, code, name):
    row = ShiftType(
        id=str(uuid.uuid4()),
        code=code,
        name=name,
        enabled=True,
        tenant_id=tenant_id,
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


# ---------------------------------------------------------------------------
# R1-12 shift_types
# ---------------------------------------------------------------------------

class TestShiftTypesAnchor:
    async def test_list_excludes_other_tenant(
        self, async_client, db_session, multi_tenant_env, admin_token_factory
    ):
        env = multi_tenant_env
        own = await _create_shift_type(db_session, env.tenant_a.id, "OPD_A", "A门诊")
        other = await _create_shift_type(db_session, env.tenant_b.id, "OPD_B", "B门诊")

        response = await async_client.get(
            "/api/v1/shift-types",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 200, response.text
        body = response.json()["data"]
        ids = {item["id"] for item in body["data"]}
        assert own.id in ids
        assert other.id not in ids
        assert body["total"] == 1

    async def test_cross_tenant_detail_404(
        self, async_client, db_session, multi_tenant_env, admin_token_factory
    ):
        env = multi_tenant_env
        other = await _create_shift_type(db_session, env.tenant_b.id, "OPD_B2", "B门诊2")

        response = await async_client.get(
            f"/api/v1/shift-types/{other.id}",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

    async def test_create_lands_on_anchor(
        self, async_client, db_session, multi_tenant_env, admin_token_factory
    ):
        env = multi_tenant_env
        response = await async_client.post(
            "/api/v1/shift-types",
            json={"code": "EVENING", "name": "晚间门诊", "enabled": True},
            headers=_auth(admin_token_factory(env.platform_admin), env.tenant_a.id),
        )
        assert response.status_code == 201, response.text
        created_id = response.json()["data"]["id"]

        row = (
            await db_session.execute(select(ShiftType).where(ShiftType.id == created_id))
        ).scalar_one()
        assert row.tenant_id == env.tenant_a.id

    async def test_cross_tenant_update_404(
        self, async_client, db_session, multi_tenant_env, admin_token_factory
    ):
        env = multi_tenant_env
        other = await _create_shift_type(db_session, env.tenant_b.id, "OPD_B3", "B门诊3")

        response = await async_client.put(
            f"/api/v1/shift-types/{other.id}",
            json={"name": "被篡改"},
            headers=_auth(admin_token_factory(env.platform_admin), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

        await db_session.refresh(other)
        assert other.name == "B门诊3"


# ---------------------------------------------------------------------------
# R1-2 settings
# ---------------------------------------------------------------------------

class TestSettingsTenantDimension:
    async def test_tenant_write_does_not_leak_to_other_tenant(
        self, async_client, db_session, multi_tenant_env, admin_token_factory
    ):
        env = multi_tenant_env
        token_a = admin_token_factory(env.admin_a)
        token_b = admin_token_factory(env.admin_b)

        write = await async_client.put(
            "/api/v1/settings/booking",
            json={"advanceDays": 20},
            headers=_auth(token_a, env.tenant_a.id),
        )
        assert write.status_code == 200, write.text

        read_a = await async_client.get(
            "/api/v1/settings/booking", headers=_auth(token_a, env.tenant_a.id)
        )
        assert read_a.status_code == 200, read_a.text
        assert read_a.json()["data"]["advanceDays"] == 20

        read_b = await async_client.get(
            "/api/v1/settings/booking", headers=_auth(token_b, env.tenant_b.id)
        )
        assert read_b.status_code == 200, read_b.text
        assert read_b.json()["data"]["advanceDays"] == 10

        rows = (
            await db_session.execute(
                select(SystemSetting).where(
                    SystemSetting.category == "booking",
                    SystemSetting.key == "advance_days",
                    SystemSetting.store_id.is_(None),
                )
            )
        ).scalars().all()
        assert {row.tenant_id for row in rows} == {env.tenant_a.id}

    async def test_platform_admin_without_tenant_400(
        self, async_client, multi_tenant_env, admin_token_factory, monkeypatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "PATIENT_ANCHOR_FAIL_CLOSE", True)
        env = multi_tenant_env
        response = await async_client.put(
            "/api/v1/settings/booking",
            json={"advanceDays": 15},
            headers=_auth(admin_token_factory(env.platform_admin)),
        )
        assert response.status_code == 400, response.text


# ---------------------------------------------------------------------------
# R1-16 notification_logs
# ---------------------------------------------------------------------------

class TestNotificationLogsAnchor:
    async def test_tenant_querying_other_tenant_403(
        self, async_client, multi_tenant_env, admin_token_factory
    ):
        env = multi_tenant_env
        response = await async_client.get(
            "/api/v1/notification-logs/usage-stats",
            params={"tenant_id": env.tenant_b.id},
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 403, response.text

    async def test_platform_admin_without_tenant_400(
        self, async_client, multi_tenant_env, admin_token_factory
    ):
        env = multi_tenant_env
        response = await async_client.get(
            "/api/v1/notification-logs/usage-stats",
            headers=_auth(admin_token_factory(env.platform_admin)),
        )
        assert response.status_code == 400, response.text

    async def test_platform_admin_with_explicit_tenant_ok(
        self, async_client, multi_tenant_env, admin_token_factory
    ):
        env = multi_tenant_env
        response = await async_client.get(
            "/api/v1/notification-logs/usage-stats",
            params={"tenant_id": env.tenant_b.id},
            headers=_auth(admin_token_factory(env.platform_admin)),
        )
        assert response.status_code == 200, response.text
        assert response.json()["data"]["total"] == 0


# ---------------------------------------------------------------------------
# R1-17 unified_message
# ---------------------------------------------------------------------------

def _event_body(tenant_id: str) -> dict:
    return {
        "tenantId": tenant_id,
        "recipientId": "patient-1",
        "recipientType": "patient",
        "templateCode": "appointment_success",
        "messageType": "appointment",
    }


class TestUnifiedMessageAnchor:
    async def test_send_body_other_tenant_403(
        self, async_client, multi_tenant_env, admin_token_factory
    ):
        env = multi_tenant_env
        response = await async_client.post(
            "/api/v1/unified-messages/send",
            json=_event_body(env.tenant_b.id),
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 403, response.text

    async def test_send_batch_body_other_tenant_403(
        self, async_client, multi_tenant_env, admin_token_factory
    ):
        env = multi_tenant_env
        response = await async_client.post(
            "/api/v1/unified-messages/send-batch",
            json=_event_body(env.tenant_b.id),
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 403, response.text

    def test_apply_tenant_anchor_overrides_body(self):
        from app.modules.unified_message.router import _apply_tenant_anchor
        from app.modules.unified_message.schemas import NotificationEvent

        event = NotificationEvent(**_event_body("tenant-same"))
        anchored = _apply_tenant_anchor(event, "tenant-same")
        assert anchored.tenant_id == "tenant-same"

    async def test_templates_follow_anchor(
        self, async_client, db_session, multi_tenant_env, admin_token_factory
    ):
        env = multi_tenant_env
        own = UnifiedTemplate(
            id=str(uuid.uuid4()),
            tenant_id=env.tenant_a.id,
            code="tpl_b3_a",
            name="A模板",
            message_type="appointment",
            status=1,
        )
        other = UnifiedTemplate(
            id=str(uuid.uuid4()),
            tenant_id=env.tenant_b.id,
            code="tpl_b3_b",
            name="B模板",
            message_type="appointment",
            status=1,
        )
        db_session.add_all([own, other])
        await db_session.commit()

        response = await async_client.get(
            "/api/v1/unified-messages/templates",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 200, response.text
        ids = {item["id"] for item in response.json()["data"]}
        assert own.id in ids
        assert other.id not in ids
