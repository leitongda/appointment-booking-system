import pytest

from app.api import deps
from app.main import app


@pytest.mark.asyncio
async def test_appointments_statistics_endpoint(async_client):
    async def override_get_current_admin():
        return {"id": "admin-1", "is_super_admin": True, "permissions": ["*"]}

    app.dependency_overrides[deps.get_current_admin] = override_get_current_admin
    try:
        response = await async_client.get("/api/v1/appointments/statistics")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    payload = response.json()["data"]
    assert "total" in payload
    assert "completed" in payload


@pytest.mark.asyncio
async def test_appointments_queue_info_requires_doctor(async_client):
    async def override_get_current_user_or_admin():
        return {"id": "user-1", "is_admin": False}

    app.dependency_overrides[deps.get_current_user_or_admin] = override_get_current_user_or_admin
    try:
        response = await async_client.get("/api/v1/appointments/queue/info")
    finally:
        app.dependency_overrides.pop(deps.get_current_user_or_admin, None)

    assert response.status_code == 403
    assert "需要医生权限" in response.text
