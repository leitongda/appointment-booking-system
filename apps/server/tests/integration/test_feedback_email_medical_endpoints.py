from datetime import datetime
from uuid import uuid4

import pytest

from app.api import deps
from app.main import app
from app.models.feedback import Feedback


@pytest.mark.asyncio
async def test_create_feedback_endpoint(async_client, db_session):
    response = await async_client.post(
        "/api/v1/feedbacks",
        json={
            "userId": "user-1",
            "userType": "patient",
            "feedbackType": "suggestion",
            "title": "功能建议",
            "content": "希望支持更多筛选条件和排序方式",
            "contact": "13800138000",
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["title"] == "功能建议"
    assert payload["content"] == "希望支持更多筛选条件和排序方式"


@pytest.mark.asyncio
async def test_email_templates_all_endpoint(async_client):
    async def override_get_current_admin():
        return {"id": "admin-1", "is_super_admin": True, "permissions": ["*"]}

    app.dependency_overrides[deps.get_current_admin] = override_get_current_admin
    try:
        response = await async_client.get("/api/v1/email-templates/all")
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)


@pytest.mark.asyncio
async def test_medical_records_my_returns_empty_without_doctor(async_client):
    async def override_get_current_user():
        return {"id": "user-1"}

    app.dependency_overrides[deps.get_current_user] = override_get_current_user
    try:
        response = await async_client.get("/api/v1/medical-records/my")
    finally:
        app.dependency_overrides.pop(deps.get_current_user, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == []
    assert payload["total"] == 0
