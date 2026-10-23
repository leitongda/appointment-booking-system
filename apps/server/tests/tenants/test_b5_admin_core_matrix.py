"""B5：管理端核心租户锚点矩阵（R1-4 / R1-5 / R1-6 / R1-19）

覆盖计划 B5 验收门：
1. freelance-fees：`/freelancers`、`/tasks`、`/settlements` 列表双向断言，
   跨租户详情 404、跨租户写非 2xx 且 DB 未变，平台管理员无 `tenant_id` 创建 400；
2. import/export：平台管理员无 `tenant_id` 导出/导入 400，A 导出不含 B 患者；
3. admin：A 的 `/admin/admins` 不含 B，跨租户 admin_id 404，平台无租户 400，
   监控端点同样要求显式锚点；
4. export / audit-logs：平台无租户 400，租户管理员传他人 tenant_id 403，
   A 只能看到 A 的数据。
"""
import uuid
from datetime import datetime
from io import BytesIO

import pytest
import pytest_asyncio
from openpyxl import load_workbook

from app.models.freelance import Freelancer, FreelanceSettlement, FreelanceTask
from app.models.rule_set import AppointmentCheckin
from app.models.user import Patient, User
from app.modules.import_export.service_import import ImportService

pytestmark = [pytest.mark.security, pytest.mark.multi_tenant]

FREELANCERS = "/api/v1/freelance-fees/freelancers"
TASKS = "/api/v1/freelance-fees/tasks"
SETTLEMENTS = "/api/v1/freelance-fees/settlements"
ADMINS = "/api/v1/admin/admins"
DATA_EXPORT = "/api/v1/data/export"
DATA_IMPORT = "/api/v1/data/import"
LEGACY_EXPORT = "/api/v1/export"
AUDIT_LOGS = "/api/v1/audit-logs"


def _auth(token: str, tenant_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id
    return headers


def _xlsx_rows(content: bytes) -> list[str]:
    """把导出的 xlsx 拍平成 "a|b|c" 文本行，便于断言包含/不包含"""
    workbook = load_workbook(BytesIO(content), read_only=True)
    sheet = workbook.active
    rows = [
        "|".join("" if value is None else str(value) for value in row)
        for row in sheet.iter_rows(values_only=True)
    ]
    workbook.close()
    return rows


async def _add_freelancer(db_session, tenant_id: str, name: str, store_id: str | None = None) -> Freelancer:
    row = Freelancer(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        store_id=store_id,
        name=name,
        phone=f"135{uuid.uuid4().int % 10**8:08d}",
        access_token=uuid.uuid4().hex,
        status=1,
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_task(
    db_session,
    tenant_id: str,
    freelancer_id: str,
    title: str,
    store_id: str | None = None,
) -> FreelanceTask:
    row = FreelanceTask(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        store_id=store_id,
        freelancer_id=freelancer_id,
        title=title,
        status="published",
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_settlement(
    db_session,
    tenant_id: str,
    freelancer_id: str,
    no: str,
    store_id: str | None = None,
) -> FreelanceSettlement:
    row = FreelanceSettlement(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        store_id=store_id,
        freelancer_id=freelancer_id,
        settlement_no=no,
        status="pending",
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_patient(db_session, tenant_id: str, name: str) -> Patient:
    user = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        phone=f"136{uuid.uuid4().int % 10**8:08d}",
        password_hash="$2b$12$test_hash_not_for_production",
        nickname=f"{name}-账号",
        status=1,
    )
    db_session.add(user)
    await db_session.flush()
    patient = Patient(
        id=str(uuid.uuid4()),
        user_id=user.id,
        tenant_id=tenant_id,
        name=name,
        phone=user.phone,
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


async def _add_checkin(db_session, factory, tenant_id: str, marker: str) -> AppointmentCheckin:
    appointment = await factory.create_appointment(
        tenant_id=tenant_id,
        patient_name=marker,
    )
    checkin = AppointmentCheckin(
        id=str(uuid.uuid4()),
        appointment_id=appointment.id,
        checkin_time=datetime.now(),
        checkin_method="MANUAL",
        status="SUCCESS",
    )
    db_session.add(checkin)
    await db_session.commit()
    await db_session.refresh(checkin)
    return checkin


@pytest_asyncio.fixture
async def b5_env(db_session, factory, multi_tenant_env):
    from app.models.admin import admin_stores

    env = multi_tenant_env

    # /admin/admins 会按 get_store_filter 默认门店收敛，测试里补上门店绑定
    await db_session.execute(
        admin_stores.insert().values(admin_id=env.admin_a.id, store_id=env.store_a.id)
    )
    await db_session.commit()

    env.freelancer_a = await _add_freelancer(
        db_session, env.tenant_a.id, "B5兼职A", env.store_a.id
    )
    env.freelancer_b = await _add_freelancer(
        db_session, env.tenant_b.id, "B5兼职B", env.store_b.id
    )
    env.task_a = await _add_task(
        db_session, env.tenant_a.id, env.freelancer_a.id, "B5任务A", env.store_a.id
    )
    env.task_b = await _add_task(
        db_session, env.tenant_b.id, env.freelancer_b.id, "B5任务B", env.store_b.id
    )
    env.settlement_a = await _add_settlement(
        db_session, env.tenant_a.id, env.freelancer_a.id, f"B5A{uuid.uuid4().hex[:10]}", env.store_a.id
    )
    env.settlement_b = await _add_settlement(
        db_session, env.tenant_b.id, env.freelancer_b.id, f"B5B{uuid.uuid4().hex[:10]}", env.store_b.id
    )
    env.patient_a = await _add_patient(db_session, env.tenant_a.id, "B5患者A")
    env.patient_b = await _add_patient(db_session, env.tenant_b.id, "B5患者B")
    env.checkin_a = await _add_checkin(db_session, factory, env.tenant_a.id, "B5签到A")
    env.checkin_b = await _add_checkin(db_session, factory, env.tenant_b.id, "B5签到B")
    return env


def _unwrap(payload: dict) -> dict:
    """兼容统一响应包装 {"code":200,"data":...}"""
    if isinstance(payload, dict) and "code" in payload and "data" in payload:
        return payload["data"]
    return payload


def _ids(payload: dict) -> set[str]:
    body = _unwrap(payload)
    if isinstance(body, dict):
        body = body.get("data") or body.get("items") or []
    return {item["id"] for item in body}


# ---------------------------------------------------------------------------
# R1-4 freelance_fees
# ---------------------------------------------------------------------------


class TestFreelanceFeesAnchor:
    async def test_freelancer_list_excludes_other_tenant(
        self, async_client, b5_env, admin_token_factory
    ):
        env = b5_env
        response = await async_client.get(
            FREELANCERS, headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.freelancer_a.id in ids
        assert env.freelancer_b.id not in ids

    async def test_task_list_excludes_other_tenant(
        self, async_client, b5_env, admin_token_factory
    ):
        env = b5_env
        response = await async_client.get(
            TASKS, headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.task_a.id in ids
        assert env.task_b.id not in ids

    async def test_settlement_list_excludes_other_tenant(
        self, async_client, b5_env, admin_token_factory
    ):
        env = b5_env
        response = await async_client.get(
            SETTLEMENTS, headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.settlement_a.id in ids
        assert env.settlement_b.id not in ids

    async def test_cross_tenant_detail_404(
        self, async_client, b5_env, admin_token_factory
    ):
        env = b5_env
        response = await async_client.get(
            f"{FREELANCERS}/{env.freelancer_b.id}",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

    async def test_cross_tenant_update_denied_and_db_unchanged(
        self, async_client, db_session, b5_env, admin_token_factory
    ):
        env = b5_env
        response = await async_client.put(
            f"{FREELANCERS}/{env.freelancer_b.id}",
            json={"name": "越权改名"},
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert not response.is_success, response.text
        stored = await db_session.get(Freelancer, env.freelancer_b.id)
        assert stored is not None and stored.name != "越权改名"

    async def test_own_create_lands_on_anchor(
        self, async_client, db_session, b5_env, admin_token_factory
    ):
        env = b5_env
        response = await async_client.post(
            FREELANCERS,
            json={"name": "B5新建兼职"},
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.is_success, response.text
        created = await db_session.get(Freelancer, _unwrap(response.json())["id"])
        assert created is not None
        assert created.tenant_id == env.tenant_a.id

    async def test_platform_admin_create_without_tenant_400(
        self, async_client, b5_env, admin_token_factory
    ):
        """写路径 anchor 为空即拒绝，不依赖灰度开关"""
        env = b5_env
        response = await async_client.post(
            FREELANCERS,
            json={"name": "平台无租户"},
            headers=_auth(admin_token_factory(env.platform_admin)),
        )
        assert response.status_code == 400, response.text


# ---------------------------------------------------------------------------
# R1-5 import_export
# ---------------------------------------------------------------------------


class TestImportExportAnchor:
    async def test_platform_admin_export_patients_400(
        self, async_client, b5_env, admin_token_factory
    ):
        env = b5_env
        response = await async_client.get(
            f"{DATA_EXPORT}/patients",
            headers=_auth(admin_token_factory(env.platform_admin)),
        )
        assert response.status_code == 400, response.text

    async def test_tenant_export_patients_excludes_other_tenant(
        self, async_client, b5_env, admin_token_factory
    ):
        env = b5_env
        response = await async_client.get(
            f"{DATA_EXPORT}/patients",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 200, response.text
        text = "\n".join(_xlsx_rows(response.content))
        assert "B5患者A" in text
        assert "B5患者B" not in text

    async def test_platform_admin_import_400(
        self, async_client, b5_env, admin_token_factory
    ):
        env = b5_env
        response = await async_client.post(
            f"{DATA_IMPORT}/doctors",
            files={"file": ("import.xlsx", b"not-an-excel", "application/vnd.ms-excel")},
            headers=_auth(admin_token_factory(env.platform_admin)),
        )
        assert response.status_code == 400, response.text

    def test_import_service_requires_explicit_tenant(self):
        """R1-5：service 不再回退请求上下文"""
        service = ImportService(db=object())
        with pytest.raises(ValueError):
            service._infer_tenant_id()


# ---------------------------------------------------------------------------
# R1-6 admin
# ---------------------------------------------------------------------------


class TestAdminAnchor:
    async def test_admin_list_excludes_other_tenant(
        self, async_client, b5_env, admin_token_factory
    ):
        env = b5_env
        response = await async_client.get(
            ADMINS, headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.admin_a.id in ids
        assert env.admin_b.id not in ids
        assert env.platform_admin.id not in ids

    async def test_cross_tenant_admin_detail_404(
        self, async_client, b5_env, admin_token_factory
    ):
        env = b5_env
        response = await async_client.get(
            f"{ADMINS}/{env.admin_b.id}",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code in (403, 404), response.text

    async def test_platform_admin_list_without_tenant_400(
        self, async_client, b5_env, admin_token_factory
    ):
        env = b5_env
        response = await async_client.get(
            ADMINS, headers=_auth(admin_token_factory(env.platform_admin))
        )
        assert response.status_code == 400, response.text

    async def test_platform_admin_monitoring_without_tenant_400(
        self, async_client, b5_env, admin_token_factory
    ):
        env = b5_env
        response = await async_client.get(
            "/api/v1/admin/logs",
            headers=_auth(admin_token_factory(env.platform_admin)),
        )
        assert response.status_code == 400, response.text

    async def test_tenant_admin_monitoring_ok(
        self, async_client, b5_env, admin_token_factory
    ):
        env = b5_env
        response = await async_client.get(
            "/api/v1/admin/logs",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 200, response.text


# ---------------------------------------------------------------------------
# R1-19 export / audit_logs
# ---------------------------------------------------------------------------


class TestExportAuditAnchor:
    async def test_legacy_export_platform_without_tenant_400(
        self, async_client, b5_env, admin_token_factory
    ):
        env = b5_env
        response = await async_client.get(
            f"{LEGACY_EXPORT}/patients",
            headers=_auth(admin_token_factory(env.platform_admin)),
        )
        assert response.status_code == 400, response.text

    async def test_legacy_export_patients_only_own_tenant(
        self, async_client, b5_env, admin_token_factory
    ):
        env = b5_env
        response = await async_client.get(
            f"{LEGACY_EXPORT}/patients",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 200, response.text
        text = "\n".join(_xlsx_rows(response.content))
        assert "B5患者A" in text
        assert "B5患者B" not in text

    async def test_audit_logs_platform_without_tenant_400(
        self, async_client, b5_env, admin_token_factory
    ):
        env = b5_env
        response = await async_client.get(
            f"{AUDIT_LOGS}/checkin-logs",
            headers=_auth(admin_token_factory(env.platform_admin)),
        )
        assert response.status_code == 400, response.text

    async def test_audit_logs_tenant_querying_other_tenant_403(
        self, async_client, b5_env, admin_token_factory
    ):
        env = b5_env
        response = await async_client.get(
            f"{AUDIT_LOGS}/checkin-logs",
            params={"tenant_id": env.tenant_b.id},
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 403, response.text

    async def test_audit_logs_only_own_tenant(
        self, async_client, b5_env, admin_token_factory
    ):
        env = b5_env
        response = await async_client.get(
            f"{AUDIT_LOGS}/checkin-logs",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.checkin_a.id in ids
        assert env.checkin_b.id not in ids
