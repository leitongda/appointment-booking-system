import pytest

from app.api import deps
from app.main import app


@pytest.mark.asyncio
async def test_doctor_booking_settings_list_endpoint(async_client):
    async def override_get_current_admin():
        return {
            "id": "admin-1",
            "is_admin": True,
            "is_super_admin": True,
            "permissions": ["*"],
            "tenant_id": None,
        }

    app.dependency_overrides[deps.get_current_admin] = override_get_current_admin
    try:
        response = await async_client.get("/api/v1/doctor-booking-settings")

        assert response.status_code == 200
        payload = response.json()
        assert payload["data"] == []
        assert payload["total"] == 0
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)


@pytest.mark.asyncio
async def test_custom_schedules_effective_endpoint(async_client):
    response = await async_client.get(
        "/api/v1/schedules/custom-schedules/effective",
        params={"start_date": "2026-03-10", "end_date": "2026-03-11"},
    )

    assert response.status_code == 200
    assert response.json()["data"] == []


@pytest.mark.asyncio
async def test_rest_days_list_endpoint(async_client):
    response = await async_client.get("/api/v1/rest-days")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == []
    assert payload["total"] == 0
