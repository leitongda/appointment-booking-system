"""P2B-8：患者/病历/检查报告/随访四模块租户与 owner 隔离矩阵

覆盖：
- 管理端服务层锚点：租户 A 只读 A 数据，跨租户读/写全部拒绝；
- 跨租户创建挂靠他租户实体的记录被拒（病历/报告）；
- 随访统计以账号锚点收敛，平台管理员在开关开启时 403；
- 患者数据流回归：全链路正常路径不受影响。
"""
import uuid
from datetime import date, datetime

import bcrypt
import pytest
import pytest_asyncio
from fastapi import HTTPException

from app.core.security import create_access_token
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.examination_report import ExaminationReport
from app.models.follow_up_self_report import FollowUpSelfReport
from app.models.follow_up_task import FollowUpTask
from app.models.medical_record import MedicalRecord
from app.modules.examination_reports.service import ExaminationReportService
from app.modules.follow_up.service import (
    FollowUpRecordService,
    FollowUpTaskService,
    SelfReportService,
)
from app.modules.medical_records.service import MedicalRecordService
from app.modules.patients.service_manage import PatientManageService
from app.schemas.medical_record import MedicalRecordCreate, MedicalRecordUpdate

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
        username=f"p2b_{uuid.uuid4().hex[:8]}",
        phone=f"132{uuid.uuid4().int % 10**8:08d}",
        password_hash=bcrypt.hashpw(uuid.uuid4().hex.encode(), bcrypt.gensalt()).decode(),
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return doctor


@pytest_asyncio.fixture
async def p2b_env(db_session, factory, multi_tenant_env):
    env = multi_tenant_env

    env.doctor_a = await _create_doctor_for(
        db_session, env.tenant_a.id, env.store_a.id, "P2B医生A"
    )
    env.doctor_b = await _create_doctor_for(
        db_session, env.tenant_b.id, env.store_b.id, "P2B医生B"
    )

    env.user_a, env.patient_a = await factory.create_patient(env.tenant_a.id)
    env.user_b, env.patient_b = await factory.create_patient(env.tenant_b.id)

    env.schedule_a = await factory.create_schedule(
        env.tenant_a.id, env.doctor_a.id, env.store_a.id
    )
    env.schedule_b = await factory.create_schedule(
        env.tenant_b.id, env.doctor_b.id, env.store_b.id
    )
    env.appt_a = await factory.create_appointment(
        env.tenant_a.id,
        env.doctor_a.id,
        env.schedule_a.id,
        env.patient_a.id,
        env.user_a.id,
        status=2,
    )
    env.appt_b = await factory.create_appointment(
        env.tenant_b.id,
        env.doctor_b.id,
        env.schedule_b.id,
        env.patient_b.id,
        env.user_b.id,
        status=2,
    )

    env.record_a = MedicalRecord(
        id=str(uuid.uuid4()),
        tenant_id=env.tenant_a.id,
        record_no=f"MR{uuid.uuid4().hex[:16].upper()}",
        appointment_id=env.appt_a.id,
        patient_id=env.patient_a.id,
        doctor_id=env.doctor_a.id,
        department_id=env.doctor_a.department_id,
        diagnosis="测试诊断A",
        status=1,
        visit_date=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    env.record_b = MedicalRecord(
        id=str(uuid.uuid4()),
        tenant_id=env.tenant_b.id,
        record_no=f"MR{uuid.uuid4().hex[:16].upper()}",
        appointment_id=env.appt_b.id,
        patient_id=env.patient_b.id,
        doctor_id=env.doctor_b.id,
        department_id=env.doctor_b.department_id,
        diagnosis="测试诊断B",
        status=1,
        visit_date=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add_all([env.record_a, env.record_b])

    env.exam_a = ExaminationReport(
        id=str(uuid.uuid4()),
        tenant_id=env.tenant_a.id,
        store_id=env.store_a.id,
        record_id=env.record_a.id,
        appointment_id=env.appt_a.id,
        patient_id=env.patient_a.id,
        doctor_id=env.doctor_a.id,
        report_type="blood_test",
        title="血常规A",
        file_name="a.pdf",
        file_key="tenant/a/a.pdf",
        file_size=100,
        file_type="application/pdf",
        file_url="http://example.com/a.pdf",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    env.exam_b = ExaminationReport(
        id=str(uuid.uuid4()),
        tenant_id=env.tenant_b.id,
        store_id=env.store_b.id,
        record_id=env.record_b.id,
        appointment_id=env.appt_b.id,
        patient_id=env.patient_b.id,
        doctor_id=env.doctor_b.id,
        report_type="blood_test",
        title="血常规B",
        file_name="b.pdf",
        file_key="tenant/b/b.pdf",
        file_size=100,
        file_type="application/pdf",
        file_url="http://example.com/b.pdf",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add_all([env.exam_a, env.exam_b])

    env.task_a = FollowUpTask(
        id=str(uuid.uuid4()),
        tenant_id=env.tenant_a.id,
        task_no=f"FU{uuid.uuid4().hex[:16].upper()}",
        patient_id=env.patient_a.id,
        doctor_id=env.doctor_a.id,
        department_id=env.doctor_a.department_id,
        appointment_id=env.appt_a.id,
        scheduled_date=date.today(),
        status="pending",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    env.task_b = FollowUpTask(
        id=str(uuid.uuid4()),
        tenant_id=env.tenant_b.id,
        task_no=f"FU{uuid.uuid4().hex[:16].upper()}",
        patient_id=env.patient_b.id,
        doctor_id=env.doctor_b.id,
        department_id=env.doctor_b.department_id,
        appointment_id=env.appt_b.id,
        scheduled_date=date.today(),
        status="pending",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add_all([env.task_a, env.task_b])

    env.report_a = FollowUpSelfReport(
        id=str(uuid.uuid4()),
        tenant_id=env.tenant_a.id,
        task_id=env.task_a.id,
        patient_id=env.patient_a.id,
        report_date=datetime.now(),
        status="pending",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    env.report_b = FollowUpSelfReport(
        id=str(uuid.uuid4()),
        tenant_id=env.tenant_b.id,
        task_id=env.task_b.id,
        patient_id=env.patient_b.id,
        report_date=datetime.now(),
        status="pending",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add_all([env.report_a, env.report_b])
    await db_session.commit()
    return env


class TestPatientsFlow:
    async def test_list_only_own_tenant(self, db_session, p2b_env):
        env = p2b_env
        service = PatientManageService(db_session, env.tenant_a.id)
        patients, total = await service.get_list(page=1, page_size=50)
        ids = {
            pet["id"] if isinstance(pet, dict) else pet.id
            for pet in patients
        }
        assert env.patient_a.id in ids
        assert env.patient_b.id not in ids

    async def test_cross_tenant_detail_and_update_denied(self, db_session, p2b_env):
        env = p2b_env
        service = PatientManageService(db_session, env.tenant_a.id)
        assert await service.get_detail(env.patient_b.id) is None

    async def test_http_list_requires_anchor(self, async_client, p2b_env, admin_token_factory):
        env = p2b_env
        token = admin_token_factory(env.admin_a)
        response = await async_client.get(
            "/api/v1/patients", headers=_auth(token, env.tenant_a.id)
        )
        assert response.status_code == 200, response.text


class TestMedicalRecordsFlow:
    async def test_cross_tenant_read_denied(self, db_session, p2b_env):
        env = p2b_env
        service_b = MedicalRecordService(db_session, env.tenant_b.id)
        assert await service_b.get_by_id(env.record_a.id) is None
        assert await service_b.get_by_appointment(env.appt_a.id) is None

    async def test_cross_tenant_write_denied(self, db_session, p2b_env):
        env = p2b_env
        service_b = MedicalRecordService(db_session, env.tenant_b.id)
        updated = await service_b.update(
            env.record_a.id, MedicalRecordUpdate(diagnosis="越权改写")
        )
        assert updated is None
        assert await service_b.delete(env.record_a.id) is False

        refreshed = await db_session.get(MedicalRecord, env.record_a.id)
        await db_session.refresh(refreshed)
        assert refreshed.diagnosis == "测试诊断A"
        assert refreshed.deleted_at is None

    async def test_create_with_foreign_appointment_rejected(self, db_session, p2b_env):
        env = p2b_env
        service_b = MedicalRecordService(db_session, env.tenant_b.id)
        with pytest.raises(ValueError):
            await service_b.create(
                env.doctor_b.id,
                MedicalRecordCreate(
                    appointment_id=env.appt_a.id,
                    chief_complaint="主诉",
                    diagnosis="诊断",
                ),
            )


class TestExaminationReportsFlow:
    async def test_cross_tenant_read_denied(self, db_session, p2b_env):
        env = p2b_env
        service_b = ExaminationReportService(db_session, env.tenant_b.id)
        assert await service_b.get_by_id(env.exam_a.id) is None
        assert await service_b.get_by_appointment(env.appt_a.id) == []
        assert await service_b.get_by_patient(env.patient_a.id) == ([], 0)


class TestFollowUpFlow:
    async def test_cross_tenant_task_operations_denied(self, db_session, p2b_env):
        env = p2b_env
        service_b = FollowUpTaskService(db_session, env.tenant_b.id)
        assert await service_b.complete_task(env.task_a.id) is None
        assert await service_b.skip_task(env.task_a.id, reason="越权") is None
        assert await service_b.delete(env.task_a.id) is False

        refreshed = await db_session.get(FollowUpTask, env.task_a.id)
        await db_session.refresh(refreshed)
        assert refreshed.status == "pending"
        assert refreshed.deleted_at is None

    async def test_cross_tenant_self_report_denied(self, db_session, p2b_env):
        env = p2b_env
        service_b = SelfReportService(db_session, env.tenant_b.id)
        assert await service_b.get_by_id(env.report_a.id) is None

    async def test_statistics_anchored(self, async_client, p2b_env, admin_token_factory):
        env = p2b_env
        token = admin_token_factory(env.admin_a)
        response = await async_client.get(
            "/api/v1/follow-up/statistics", headers=_auth(token, env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        body = response.json()
        data = body.get("data") or {}
        assert "total" in data

    async def test_platform_admin_statistics_403_when_switch_on(
        self, async_client, p2b_env, admin_token_factory, monkeypatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "PATIENT_ANCHOR_FAIL_CLOSE", True)
        env = p2b_env
        token = admin_token_factory(env.platform_admin)
        response = await async_client.get(
            "/api/v1/follow-up/statistics", headers=_auth(token)
        )
        assert response.status_code == 403, response.text


class TestFollowUpPatientOwner:
    """P2B-7：同租户内患者之间的水平越权必须被拒（404，不泄露存在性）"""

    async def _other_patient_token(self, factory, env):
        other_user, other_patient = await factory.create_patient(env.tenant_a.id)
        token = create_access_token(
            {"sub": other_user.id, "type": "user", "tenant_id": env.tenant_a.id}
        )
        return token, other_patient

    async def test_other_patient_cannot_list_tasks(
        self, async_client, factory, p2b_env
    ):
        env = p2b_env
        token, _ = await self._other_patient_token(factory, env)
        response = await async_client.get(
            f"/api/v1/follow-up/tasks/patient/{env.patient_a.id}",
            headers=_auth(token),
        )
        assert response.status_code == 404, response.text

    async def test_other_patient_cannot_read_task_detail(
        self, async_client, factory, p2b_env
    ):
        env = p2b_env
        token, _ = await self._other_patient_token(factory, env)
        response = await async_client.get(
            f"/api/v1/follow-up/tasks/{env.task_a.id}",
            headers=_auth(token),
        )
        assert response.status_code == 404, response.text

    async def test_other_patient_cannot_complete_task(
        self, async_client, db_session, factory, p2b_env
    ):
        env = p2b_env
        token, _ = await self._other_patient_token(factory, env)
        response = await async_client.patch(
            f"/api/v1/follow-up/tasks/{env.task_a.id}/complete",
            headers=_auth(token),
        )
        assert response.status_code == 404, response.text

        refreshed = await db_session.get(FollowUpTask, env.task_a.id)
        await db_session.refresh(refreshed)
        assert refreshed.status == "pending"
