"""statistics 聚合查询的租户隔离测试（B4 / R1-3）

验收口径：
- 租户 B 的预约/患者/医生不计入租户 A 的统计结果，双向断言；
- 无门店绑定的租户管理员（store_ids=[]）只能看到本租户全量，不得看到平台全量；
- 排行/分布/汇总类聚合同样带租户条件。

平台管理员（is_super_admin=True）仍保持全平台视图。
"""
import uuid
from datetime import date, datetime, time

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import get_password_hash
from app.main import app
from app.models.appointment import Appointment
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.store import Store
from app.models.tenant import Tenant
from app.models.user import Patient, User

# ==================== 数据构造 ====================

async def _create_tenant_dataset(db: AsyncSession, code: str) -> dict:
    """为一个租户创建：门店/科室/医生/用户/患者/排班/今日预约"""
    tenant = Tenant(id=str(uuid.uuid4()), tenant_code=code, name=f"统计租户-{code}", status=1)
    db.add(tenant)

    store = Store(
        id=str(uuid.uuid4()), tenant_id=tenant.id, name=f"{code}-门店", code=f"{code}_store", status=1
    )
    db.add(store)

    department = Department(
        id=str(uuid.uuid4()), tenant_id=tenant.id, store_id=store.id, name=f"{code}-科室", status=1
    )
    db.add(department)

    doctor = Doctor(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        store_id=store.id,
        department_id=department.id,
        name=f"{code}-医生",
        username=f"{code}_doctor",
        phone=f"139{code[-3:].zfill(8)}",
        password_hash=get_password_hash("password123"),
        status=1,
    )
    db.add(doctor)

    user = User(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        phone=f"138{code[-3:].zfill(8)}",
        password_hash=get_password_hash("password123"),
        nickname=f"{code}-用户",
        status=1,
    )
    db.add(user)

    patient = Patient(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        store_id=store.id,
        user_id=user.id,
        name=f"{code}-患者",
        phone=user.phone,
    )
    db.add(patient)

    today = date.today()
    schedule = Schedule(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        doctor_id=doctor.id,
        store_id=store.id,
        schedule_date=today,
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=50,
        booked_slots=1,
        status=1,
    )
    db.add(schedule)

    appointment = Appointment(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        appointment_no=f"ST{uuid.uuid4().hex[:12].upper()}",
        user_id=user.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        schedule_id=schedule.id,
        queue_number=1,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(appointment)

    await db.commit()
    return {
        "tenant": tenant,
        "store": store,
        "department": department,
        "doctor": doctor,
        "user": user,
        "patient": patient,
        "schedule": schedule,
        "appointment": appointment,
    }


@pytest_asyncio.fixture
async def stats_data(db_session: AsyncSession) -> dict:
    dataset_a = await _create_tenant_dataset(db_session, "stats_a")
    dataset_b = await _create_tenant_dataset(db_session, "stats_b")
    return {"a": dataset_a, "b": dataset_b}


def _admin_of(tenant: Tenant) -> dict:
    """租户管理员：无门店绑定（store_ids=[]），用于验证不得看平台全量"""
    return {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant.id,
        "role_type": "admin",
        "is_admin": True,
        "is_super_admin": False,
        "is_platform_admin": False,
        "is_tenant_admin": True,
        "is_store_admin": False,
        "store_ids": [],
        "current_store_id": None,
        "permissions": ["*"],
    }


def _platform_admin() -> dict:
    return {
        "id": str(uuid.uuid4()),
        "tenant_id": None,
        "role_type": "admin",
        "is_admin": True,
        "is_super_admin": True,
        "is_platform_admin": True,
        "store_ids": [],
        "permissions": ["*"],
    }


def _override_admin(admin: dict):
    async def _dep():
        return admin

    return _dep


# ==================== 概览：双向断言 ====================

@pytest.mark.asyncio
@pytest.mark.parametrize("side", ["a", "b"])
async def test_overview_counts_only_own_tenant(
    async_client: AsyncClient, stats_data: dict, side: str
):
    """A/B 各自的 /overview 只统计本租户数据（无门店绑定也不得看全量）"""
    own = stats_data[side]
    app.dependency_overrides[deps.get_current_admin] = _override_admin(_admin_of(own["tenant"]))
    try:
        response = await async_client.get("/api/v1/statistics/overview")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["totalPatients"] == 1
    assert data["totalDoctors"] == 1
    assert data["todayAppointments"] == 1
    assert data["monthAppointments"] == 1
    assert data["todayVisits"] == 0


@pytest.mark.asyncio
async def test_overview_platform_admin_sees_all(async_client: AsyncClient, stats_data: dict):
    """平台管理员（tenant_id=None）保持全平台视图"""
    app.dependency_overrides[deps.get_current_admin] = _override_admin(_platform_admin())
    try:
        response = await async_client.get("/api/v1/statistics/overview")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["totalPatients"] == 2
    assert data["totalDoctors"] == 2
    assert data["todayAppointments"] == 2


# ==================== 预约统计聚合 ====================

@pytest.mark.asyncio
async def test_appointment_status_stats_scoped(async_client: AsyncClient, stats_data: dict):
    own = stats_data["a"]
    app.dependency_overrides[deps.get_current_admin] = _override_admin(_admin_of(own["tenant"]))
    try:
        response = await async_client.get("/api/v1/statistics/appointments/status")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    rows = response.json()["data"]
    assert sum(row["count"] for row in rows) == 1


@pytest.mark.asyncio
async def test_appointment_summary_scoped(async_client: AsyncClient, stats_data: dict):
    own = stats_data["a"]
    app.dependency_overrides[deps.get_current_admin] = _override_admin(_admin_of(own["tenant"]))
    try:
        response = await async_client.get("/api/v1/statistics/appointments/summary")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1


@pytest.mark.asyncio
async def test_appointment_trend_scoped(async_client: AsyncClient, stats_data: dict):
    own = stats_data["a"]
    app.dependency_overrides[deps.get_current_admin] = _override_admin(_admin_of(own["tenant"]))
    try:
        response = await async_client.get("/api/v1/statistics/appointments/trend?days=1")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    trend = response.json()["data"]
    assert len(trend) == 1
    assert trend[0]["count"] == 1


# ==================== 排行与分布聚合 ====================

@pytest.mark.asyncio
async def test_doctor_ranking_scoped(async_client: AsyncClient, stats_data: dict):
    own = stats_data["a"]
    app.dependency_overrides[deps.get_current_admin] = _override_admin(_admin_of(own["tenant"]))
    try:
        response = await async_client.get("/api/v1/statistics/doctors/ranking")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    rows = response.json()["data"]
    assert [row["doctorId"] for row in rows] == [own["doctor"].id]


@pytest.mark.asyncio
async def test_department_ranking_scoped(async_client: AsyncClient, stats_data: dict):
    own = stats_data["a"]
    app.dependency_overrides[deps.get_current_admin] = _override_admin(_admin_of(own["tenant"]))
    try:
        response = await async_client.get("/api/v1/statistics/departments/ranking")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    rows = response.json()["data"]
    assert [row["departmentId"] for row in rows] == [own["department"].id]


@pytest.mark.asyncio
async def test_store_ranking_scoped(async_client: AsyncClient, stats_data: dict):
    own = stats_data["a"]
    app.dependency_overrides[deps.get_current_admin] = _override_admin(_admin_of(own["tenant"]))
    try:
        response = await async_client.get("/api/v1/statistics/stores/ranking")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    rows = response.json()["data"]
    assert [row["storeId"] for row in rows] == [own["store"].id]


@pytest.mark.asyncio
async def test_time_slot_distribution_scoped(async_client: AsyncClient, stats_data: dict):
    own = stats_data["a"]
    app.dependency_overrides[deps.get_current_admin] = _override_admin(_admin_of(own["tenant"]))
    try:
        response = await async_client.get("/api/v1/statistics/time-slots/distribution")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    rows = response.json()["data"]
    assert sum(row["count"] for row in rows) == 1
