import pytest

from app.api import deps
from app.main import app


@pytest.mark.asyncio
async def test_audit_logs_statistics_endpoint(async_client):
    async def override_get_current_admin():
        return {"id": "admin-1", "is_super_admin": True, "permissions": ["*"]}

    app.dependency_overrides[deps.get_current_admin] = override_get_current_admin
    try:
        # R1-19：平台管理员必须显式指定租户
        response = await async_client.get(
            "/api/v1/audit-logs/checkin-logs/statistics",
            params={"tenant_id": "tenant-1"},
        )
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["data"] == []
    assert payload["total"] == 0
