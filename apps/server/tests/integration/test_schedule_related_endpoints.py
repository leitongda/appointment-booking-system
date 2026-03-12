import pytest


@pytest.mark.asyncio
async def test_doctor_booking_settings_list_endpoint(async_client):
    response = await async_client.get("/api/v1/doctor-booking-settings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == []
    assert payload["total"] == 0


@pytest.mark.asyncio
async def test_custom_schedules_effective_endpoint(async_client):
    response = await async_client.get(
        "/api/v1/custom-schedules/effective",
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
