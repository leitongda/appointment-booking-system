from uuid import uuid4

import pytest

from app.api import deps
from app.main import app
from app.models.message import MessageTemplate


@pytest.mark.asyncio
async def test_messages_unread_count_endpoint(async_client):
    response = await async_client.get(
        "/api/v1/messages/unread-count",
        params={"user_id": "user-1", "user_type": "patient"},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["total"] == 0


@pytest.mark.asyncio
async def test_message_templates_endpoint(async_client, db_session):
    template = MessageTemplate(
        id=str(uuid4()),
        name="系统通知模板",
        code="sys_notice",
        title_template="系统通知",
        content_template="内容",
        message_type="system",
        status=1,
    )
    db_session.add(template)
    await db_session.commit()

    async def override_get_current_admin():
        return {"id": "admin-1", "is_super_admin": True, "permissions": ["*"]}

    app.dependency_overrides[deps.get_current_admin] = override_get_current_admin
    try:
        response = await async_client.get("/api/v1/messages/templates")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload[0]["name"] == "系统通知模板"
