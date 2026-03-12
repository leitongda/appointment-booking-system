from datetime import datetime
from uuid import uuid4

import pytest

from app.api import deps
from app.main import app
from app.models.admin import Admin, Role


@pytest.mark.asyncio
async def test_admin_public_key_endpoint(async_client):
    response = await async_client.get("/api/v1/admin/public-key")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert payload["data"]["publicKey"]


@pytest.mark.asyncio
async def test_admin_me_endpoint_with_override(async_client, db_session):
    role = Role(
        id=str(uuid4()),
        name="超级管理员",
        code="SUPER_ADMIN",
        status=1,
        permissions="[]",
    )
    admin = Admin(
        id=str(uuid4()),
        username="root",
        password_hash="hashed",
        name="Root",
        role_id=role.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add_all([role, admin])
    await db_session.commit()

    async def override_get_current_admin():
        return {"id": admin.id, "is_super_admin": True}

    app.dependency_overrides[deps.get_current_admin] = override_get_current_admin
    try:
        response = await async_client.get("/api/v1/admin/me")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["id"] == admin.id
    assert payload["username"] == "root"
    assert payload["isSuperAdmin"] is True


@pytest.mark.asyncio
async def test_doctor_portal_me_endpoint(async_client, test_doctor, test_store, test_department):
    test_doctor.store = test_store
    test_doctor.department = test_department

    async def override_get_current_doctor():
        return test_doctor

    app.dependency_overrides[deps.get_current_doctor_by_token] = override_get_current_doctor
    try:
        response = await async_client.get("/api/v1/doctor-portal/me")
    finally:
        app.dependency_overrides.pop(deps.get_current_doctor_by_token, None)

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["id"] == test_doctor.id
    assert payload["store_id"] == test_store.id
    assert payload["department_id"] == test_department.id
