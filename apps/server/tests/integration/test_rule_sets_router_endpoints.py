from unittest.mock import AsyncMock, patch

import pytest

from app.api import deps
from app.main import app


@pytest.mark.asyncio
async def test_rule_sets_performance_endpoint(async_client):
    async def override_get_current_super_admin():
        return {"id": "admin-1", "is_super_admin": True, "permissions": ["*"]}

    app.dependency_overrides[deps.get_current_super_admin] = override_get_current_super_admin
    try:
        with patch(
            "app.services.rule_performance_service.performance_monitor.get_performance_stats",
            new=AsyncMock(return_value={"operation": None, "hours": 24, "stats": []}),
        ):
            response = await async_client.get("/api/v1/rule-sets/performance")
    finally:
        app.dependency_overrides.pop(deps.get_current_super_admin, None)

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["hours"] == 24
    assert payload["stats"] == []


@pytest.mark.asyncio
async def test_rule_sets_clear_metrics_endpoint(async_client):
    async def override_get_current_super_admin():
        return {"id": "admin-1", "is_super_admin": True, "permissions": ["*"]}

    app.dependency_overrides[deps.get_current_super_admin] = override_get_current_super_admin
    try:
        with patch(
            "app.services.rule_performance_service.performance_monitor.clear_metrics",
            new=AsyncMock(return_value={"success": True, "cleared": 3}),
        ):
            response = await async_client.delete("/api/v1/rule-sets/performance/metrics")
    finally:
        app.dependency_overrides.pop(deps.get_current_super_admin, None)

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["success"] is True
    assert payload["cleared"] == 3
