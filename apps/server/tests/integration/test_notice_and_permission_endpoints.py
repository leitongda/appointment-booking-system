from datetime import datetime
from uuid import uuid4

import pytest

from app.api import deps
from app.main import app
from app.models.booking_notice import BookingNotice


@pytest.mark.asyncio
async def test_booking_notice_public_endpoint(async_client, db_session):
    notice = BookingNotice(
        id=str(uuid4()),
        type="BOOKING",
        title="预约须知",
        content="请提前十分钟到场",
        sort_order=1,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(notice)
    await db_session.commit()

    response = await async_client.get("/api/v1/booking-notices/public")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload[0]["title"] == "预约须知"
    assert payload[0]["type"] == "BOOKING"


@pytest.mark.asyncio
async def test_store_email_recipient_event_types(async_client):
    async def override_get_current_admin():
        return {"id": "admin-1", "is_super_admin": True, "permissions": ["*"]}

    app.dependency_overrides[deps.get_current_admin] = override_get_current_admin
    try:
        response = await async_client.get("/api/v1/store-email-recipients/event-types")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    payload = response.json()["data"]
    assert isinstance(payload, list)
    assert payload
    assert "value" in payload[0]
    assert "label" in payload[0]


@pytest.mark.asyncio
async def test_permission_denied_returns_403(async_client):
    async def override_get_current_admin():
        return {"id": "admin-1", "is_super_admin": False, "permissions": []}

    app.dependency_overrides[deps.get_current_admin] = override_get_current_admin
    try:
        response = await async_client.post(
            "/api/v1/content/news",
            json={
                "title": "无权限新闻",
                "type": 1,
                "content": "body",
                "isTop": 0,
                "status": 0,
            },
        )
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 403
    payload = response.json()
    assert payload["code"] == 403
