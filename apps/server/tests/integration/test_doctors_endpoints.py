from uuid import uuid4

import pytest

from app.models.department import Department
from app.models.doctor import Doctor
from app.models.store import Store


@pytest.mark.asyncio
async def test_doctor_public_endpoint(async_client, db_session, test_tenant):
    store = Store(id=str(uuid4()), name="公开门店", status=1, tenant_id=test_tenant.id)
    department = Department(id=str(uuid4()), name="公开科室", status=1, store_id=store.id, tenant_id=test_tenant.id)
    doctor = Doctor(
        id=str(uuid4()),
        store_id=store.id,
        department_id=department.id,
        name="公开医生",
        username="doctor_public",
        status=1,
        tenant_id=test_tenant.id,
    )
    db_session.add_all([store, department, doctor])
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/doctors/public/{doctor.id}",
        headers={"X-Tenant-ID": test_tenant.id},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["id"] == doctor.id
    assert payload["name"] == "公开医生"


@pytest.mark.asyncio
async def test_doctor_login_rejects_invalid_credentials(async_client):
    response = await async_client.post(
        "/api/v1/doctors/login",
        json={"phone": "13800138000", "password": "wrong-password"},
    )

    assert response.status_code == 401
    payload = response.json()
    assert payload["code"] == 401
