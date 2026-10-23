"""B6：流程与排班配套租户锚点矩阵（R1-7 / R1-8 / R1-9 / R1-10）

覆盖计划 B6 验收门：
1. approval-flows：A 列表双向断言、跨租户详情 404、创建锚点为空 400、
   正控创建落库 tenant_id=A；
2. approval-instances：A 列表双向断言、跨租户处置 404 且 DB 未变；
3. rule-sets：A 列表双向断言、跨租户详情/写入 404、伪造租户头 403、
   平台管理员无 tenant_id 在 fail-close 下 400；
4. schedule-suspensions：A 列表双向断言、跨租户取消/处置 404 且 DB 未变；
5. rest-days / leave-requests：A 列表双向断言、跨租户取消/审批 404 且 DB 未变。
"""
import json
import uuid
from datetime import date, datetime, timedelta

import pytest
import pytest_asyncio

from app.models.approval_flow import ApprovalFlowDefinition, ApprovalInstance
from app.models.leave_request import LeaveRequest
from app.models.rest_day import RestDay
from app.models.rule_set import RuleSet
from app.models.schedule_suspension import ScheduleSuspension

pytestmark = [pytest.mark.security, pytest.mark.multi_tenant]

APPROVAL_FLOWS = "/api/v1/approval-flows"
APPROVAL_INSTANCES = "/api/v1/approval-instances"
RULE_SETS = "/api/v1/rule-sets"
SUSPENSIONS = "/api/v1/schedule-suspensions"
REST_DAYS = "/api/v1/rest-days"
LEAVE_REQUESTS = "/api/v1/leave-requests"


def _auth(token: str, tenant_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id
    return headers


def _items(payload) -> list:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    if "data" in payload:
        data = payload["data"]
        return data if isinstance(data, list) else (data.get("data") or data.get("items") or [])
    return payload.get("items") or []


def _ids(payload) -> set[str]:
    return {item.get("id") for item in _items(payload) if isinstance(item, dict)}


async def _add_flow_def(db_session, tenant_id: str, name: str) -> ApprovalFlowDefinition:
    row = ApprovalFlowDefinition(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=name,
        business_type="custom",
        version=1,
        status="draft",
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_instance(
    db_session, tenant_id: str, flow_def_id: str, applicant_id: str, title: str
) -> ApprovalInstance:
    row = ApprovalInstance(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        flow_def_id=flow_def_id,
        business_type="custom",
        business_id=str(uuid.uuid4()),
        title=title,
        form_data={},
        status="pending",
        applicant_id=applicant_id,
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_rule_set(db_session, tenant_id: str, name: str) -> RuleSet:
    row = RuleSet(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=name,
        enabled=True,
        priority=100,
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_suspension(db_session, tenant_id: str, store_id: str, doctor_id: str, title: str):
    row = ScheduleSuspension(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        store_id=store_id,
        doctor_id=doctor_id,
        title=title,
        suspension_date=date.today() + timedelta(days=5),
        schedule_ids=json.dumps([str(uuid.uuid4())]),
        status=1,
        suspension_type="temporary",
        processing_status="pending",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_rest_day(db_session, tenant_id: str, store_id: str, doctor_id: str, reason: str):
    row = RestDay(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        store_id=store_id,
        doctor_ids=json.dumps([doctor_id]),
        reason=reason,
        start_date=date.today() + timedelta(days=6),
        end_date=date.today() + timedelta(days=7),
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_leave_request(db_session, tenant_id: str, doctor_id: str, reason: str):
    row = LeaveRequest(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        doctor_id=doctor_id,
        request_type="stop_clinic",
        stop_date=date.today() + timedelta(days=8),
        stop_period="morning",
        reason=reason,
        status="pending",
        affected_appointments=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


@pytest_asyncio.fixture
async def b6_env(db_session, factory, multi_tenant_env):
    """A/B 两租户各一套流程定义、实例、规则组、停诊、休息日、停诊申请"""
    env = multi_tenant_env

    env.doctor_a = await factory.create_doctor(env.tenant_a.id, env.store_a.id, name="B6医生A")
    env.doctor_b = await factory.create_doctor(env.tenant_b.id, env.store_b.id, name="B6医生B")

    env.flow_def_a = await _add_flow_def(db_session, env.tenant_a.id, "A流程")
    env.flow_def_b = await _add_flow_def(db_session, env.tenant_b.id, "B流程")
    env.instance_a = await _add_instance(
        db_session, env.tenant_a.id, env.flow_def_a.id, env.admin_a.id, "A审批"
    )
    env.instance_b = await _add_instance(
        db_session, env.tenant_b.id, env.flow_def_b.id, env.admin_b.id, "B审批"
    )
    env.rule_set_a = await _add_rule_set(db_session, env.tenant_a.id, "A规则组")
    env.rule_set_b = await _add_rule_set(db_session, env.tenant_b.id, "B规则组")
    env.suspension_a = await _add_suspension(
        db_session, env.tenant_a.id, env.store_a.id, env.doctor_a.id, "A停诊"
    )
    env.suspension_b = await _add_suspension(
        db_session, env.tenant_b.id, env.store_b.id, env.doctor_b.id, "B停诊"
    )
    env.rest_day_a = await _add_rest_day(
        db_session, env.tenant_a.id, env.store_a.id, env.doctor_a.id, "A休息"
    )
    env.rest_day_b = await _add_rest_day(
        db_session, env.tenant_b.id, env.store_b.id, env.doctor_b.id, "B休息"
    )
    env.leave_a = await _add_leave_request(db_session, env.tenant_a.id, env.doctor_a.id, "A停诊申请")
    env.leave_b = await _add_leave_request(db_session, env.tenant_b.id, env.doctor_b.id, "B停诊申请")
    return env


class TestApprovalFlowsAnchor:
    async def test_list_only_own_tenant(self, async_client, b6_env, admin_token_factory):
        env = b6_env
        response = await async_client.get(
            APPROVAL_FLOWS, headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.flow_def_a.id in ids
        assert env.flow_def_b.id not in ids

    async def test_cross_tenant_detail_404(self, async_client, b6_env, admin_token_factory):
        env = b6_env
        response = await async_client.get(
            f"{APPROVAL_FLOWS}/{env.flow_def_b.id}",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

    async def test_create_without_anchor_400(self, async_client, b6_env, admin_token_factory):
        env = b6_env
        response = await async_client.post(
            APPROVAL_FLOWS,
            headers=_auth(admin_token_factory(env.platform_admin)),
            json={"name": "无锚点流程", "businessType": "custom", "nodes": []},
        )
        assert response.status_code == 400, response.text

    async def test_create_writes_tenant_anchor(
        self, async_client, db_session, b6_env, admin_token_factory
    ):
        env = b6_env
        response = await async_client.post(
            APPROVAL_FLOWS,
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
            json={"name": f"锚点流程{uuid.uuid4().hex[:6]}", "businessType": "custom", "nodes": []},
        )
        assert response.status_code in (200, 201), response.text
        body = response.json()
        created_id = body.get("id") or (body.get("data") or {}).get("id")
        created = await db_session.get(ApprovalFlowDefinition, created_id)
        assert created is not None
        assert created.tenant_id == env.tenant_a.id


class TestApprovalInstancesAnchor:
    async def test_list_only_own_tenant(self, async_client, b6_env, admin_token_factory):
        env = b6_env
        response = await async_client.get(
            APPROVAL_INSTANCES,
            params={"view": "initiated"},
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.instance_a.id in ids
        assert env.instance_b.id not in ids

    async def test_cross_tenant_approve_404_and_unchanged(
        self, async_client, db_session, b6_env, admin_token_factory
    ):
        env = b6_env
        response = await async_client.post(
            f"{APPROVAL_INSTANCES}/{env.instance_b.id}/approve",
            json={"comment": "越权审批"},
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

        refreshed = await db_session.get(ApprovalInstance, env.instance_b.id)
        await db_session.refresh(refreshed)
        assert refreshed.status == "pending"

    async def test_cross_tenant_withdraw_404_and_unchanged(
        self, async_client, db_session, b6_env, admin_token_factory
    ):
        env = b6_env
        response = await async_client.post(
            f"{APPROVAL_INSTANCES}/{env.instance_b.id}/withdraw",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

        refreshed = await db_session.get(ApprovalInstance, env.instance_b.id)
        await db_session.refresh(refreshed)
        assert refreshed.status == "pending"


class TestRuleSetsAnchor:
    async def test_list_only_own_tenant(self, async_client, b6_env, admin_token_factory):
        env = b6_env
        response = await async_client.get(
            RULE_SETS, headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.rule_set_a.id in ids
        assert env.rule_set_b.id not in ids

    async def test_cross_tenant_detail_404(self, async_client, b6_env, admin_token_factory):
        env = b6_env
        response = await async_client.get(
            f"{RULE_SETS}/{env.rule_set_b.id}",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

    async def test_cross_tenant_write_404_and_unchanged(
        self, async_client, db_session, b6_env, admin_token_factory
    ):
        env = b6_env
        # 规则组写接口仅超管可调：显式锚定 A 后越权写 B 应视为不存在
        response = await async_client.put(
            f"{RULE_SETS}/{env.rule_set_b.id}",
            params={"tenant_id": env.tenant_a.id},
            json={"name": "被越权改名"},
            headers=_auth(admin_token_factory(env.platform_admin)),
        )
        assert response.status_code == 404, response.text

        refreshed = await db_session.get(RuleSet, env.rule_set_b.id)
        await db_session.refresh(refreshed)
        assert refreshed.name == "B规则组"

    async def test_forged_tenant_header_403(self, async_client, b6_env, admin_token_factory):
        env = b6_env
        response = await async_client.get(
            RULE_SETS, headers=_auth(admin_token_factory(env.admin_a), env.tenant_b.id)
        )
        assert response.status_code == 403, response.text

    async def test_platform_admin_without_tenant_400_in_fail_close(
        self, async_client, b6_env, admin_token_factory, monkeypatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "PATIENT_ANCHOR_FAIL_CLOSE", True)
        env = b6_env
        response = await async_client.get(
            RULE_SETS, headers=_auth(admin_token_factory(env.platform_admin))
        )
        assert response.status_code == 400, response.text

    async def test_platform_admin_explicit_tenant_scoped(
        self, async_client, b6_env, admin_token_factory
    ):
        env = b6_env
        response = await async_client.get(
            RULE_SETS,
            params={"tenant_id": env.tenant_b.id},
            headers=_auth(admin_token_factory(env.platform_admin)),
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.rule_set_b.id in ids
        assert env.rule_set_a.id not in ids


class TestScheduleSuspensionsAnchor:
    async def test_list_only_own_tenant(self, async_client, b6_env, admin_token_factory):
        env = b6_env
        response = await async_client.get(
            SUSPENSIONS, headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.suspension_a.id in ids
        assert env.suspension_b.id not in ids

    async def test_cross_tenant_cancel_404_and_unchanged(
        self, async_client, db_session, b6_env, admin_token_factory
    ):
        env = b6_env
        response = await async_client.put(
            f"{SUSPENSIONS}/{env.suspension_b.id}/cancel",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

        refreshed = await db_session.get(ScheduleSuspension, env.suspension_b.id)
        await db_session.refresh(refreshed)
        assert refreshed.status == 1

    async def test_cross_tenant_process_404(self, async_client, db_session, b6_env, admin_token_factory):
        env = b6_env
        response = await async_client.post(
            f"{SUSPENSIONS}/{env.suspension_b.id}/process",
            json={"processingMethod": "manual"},
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

        refreshed = await db_session.get(ScheduleSuspension, env.suspension_b.id)
        await db_session.refresh(refreshed)
        assert refreshed.processing_status == "pending"

    async def test_create_writes_tenant_anchor(
        self, async_client, db_session, b6_env, admin_token_factory
    ):
        env = b6_env
        response = await async_client.post(
            SUSPENSIONS,
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
            json={
                "storeId": env.store_a.id,
                "doctorId": env.doctor_a.id,
                "title": "正控停诊",
                "suspensionDate": str(date.today() + timedelta(days=11)),
            },
        )
        assert response.status_code in (200, 201), response.text
        body = response.json()
        created_id = body.get("id") or (body.get("data") or {}).get("id")
        created = await db_session.get(ScheduleSuspension, created_id)
        assert created is not None
        assert created.tenant_id == env.tenant_a.id

    async def test_platform_admin_create_without_tenant_400(
        self, async_client, b6_env, admin_token_factory
    ):
        env = b6_env
        response = await async_client.post(
            SUSPENSIONS,
            headers=_auth(admin_token_factory(env.platform_admin)),
            json={
                "storeId": env.store_b.id,
                "doctorId": env.doctor_b.id,
                "title": "无锚点停诊",
                "suspensionDate": str(date.today() + timedelta(days=9)),
            },
        )
        assert response.status_code == 400, response.text


class TestRestDaysAnchor:
    async def test_list_only_own_tenant(self, async_client, b6_env, admin_token_factory):
        env = b6_env
        response = await async_client.get(
            REST_DAYS, headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.rest_day_a.id in ids
        assert env.rest_day_b.id not in ids

    async def test_cross_tenant_cancel_404_and_unchanged(
        self, async_client, db_session, b6_env, admin_token_factory
    ):
        env = b6_env
        response = await async_client.put(
            f"{REST_DAYS}/{env.rest_day_b.id}/cancel",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

        refreshed = await db_session.get(RestDay, env.rest_day_b.id)
        await db_session.refresh(refreshed)
        assert refreshed.status == 1


class TestLeaveRequestsAnchor:
    async def test_list_only_own_tenant(self, async_client, b6_env, admin_token_factory):
        env = b6_env
        response = await async_client.get(
            LEAVE_REQUESTS, headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.leave_a.id in ids
        assert env.leave_b.id not in ids

    async def test_pending_count_scoped(self, async_client, b6_env, admin_token_factory):
        env = b6_env
        response = await async_client.get(
            f"{LEAVE_REQUESTS}/pending-count",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 200, response.text
        # A 租户仅 1 条待审核（上面 list 用例的 B 申请不得计入）
        assert response.json()["data"]["count"] == 1, response.text

    async def test_cross_tenant_review_404_and_unchanged(
        self, async_client, db_session, b6_env, admin_token_factory
    ):
        env = b6_env
        response = await async_client.post(
            f"{LEAVE_REQUESTS}/{env.leave_b.id}/review",
            json={"status": "approved", "reviewComment": "越权审批"},
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

        refreshed = await db_session.get(LeaveRequest, env.leave_b.id)
        await db_session.refresh(refreshed)
        assert refreshed.status == "pending"
