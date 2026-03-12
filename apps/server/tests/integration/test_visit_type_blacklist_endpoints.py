import pytest

from app.api import deps
from app.main import app


@pytest.mark.asyncio
async def test_store_visit_type_default_config(async_client):
    async def override_get_current_admin():
        return {"id": "admin-1", "is_super_admin": True, "permissions": ["*"]}

    app.dependency_overrides[deps.get_current_admin] = override_get_current_admin
    try:
        response = await async_client.get("/api/v1/visit-type-configs/store/store-1")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["storeId"] == "store-1"
    assert payload["timeLimit"] == 30


@pytest.mark.asyncio
async def test_blacklist_check_endpoint(async_client):
    response = await async_client.post("/api/v1/blacklists/check", params={"phone": "13800138000"})

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["is_blacklisted"] is False
