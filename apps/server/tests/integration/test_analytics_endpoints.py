from unittest.mock import patch

import pytest

from app.api import deps
from app.main import app


@pytest.mark.asyncio
async def test_analytics_track_endpoint(async_client):
    with patch("app.tasks.behavior_log_task.save_behavior_log") as mock_task:
        mock_task.delay.return_value = None
        response = await async_client.post(
            "/api/v1/analytics/track",
            json={
                "platform": "h5",
                "sessionId": "session-1",
                "eventType": "page_view",
                "pagePath": "/home",
                "pageTitle": "首页",
            },
        )

    assert response.status_code == 200
    assert response.json()["data"]["success"] is True


@pytest.mark.asyncio
async def test_analytics_overview_endpoint(async_client):
    async def override_get_current_admin():
        return {"id": "admin-1", "is_super_admin": True, "permissions": ["*"]}

    app.dependency_overrides[deps.get_current_admin] = override_get_current_admin
    try:
        response = await async_client.get("/api/v1/analytics/overview")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    payload = response.json()["data"]
    assert "totalPageViews" in payload
    assert "dailyStats" in payload
