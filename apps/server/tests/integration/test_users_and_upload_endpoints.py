from io import BytesIO
from uuid import uuid4

import pytest

from app.api import deps
from app.main import app
from app.models.user import User


@pytest.mark.asyncio
async def test_users_profile_endpoint(async_client, db_session):
    user = User(
        id=str(uuid4()),
        phone="13800138009",
        password_hash="hashed",
        nickname="测试用户资料",
        status=1,
    )
    db_session.add(user)
    await db_session.commit()

    async def override_get_current_user():
        return {"id": user.id}

    app.dependency_overrides[deps.get_current_user] = override_get_current_user
    try:
        response = await async_client.get("/api/v1/users/profile")
    finally:
        app.dependency_overrides.pop(deps.get_current_user, None)

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["id"] == user.id
    assert payload["nickname"] == "测试用户资料"


@pytest.mark.asyncio
async def test_upload_rejects_invalid_content_type(async_client):
    async def override_get_current_admin():
        return {"id": "admin-1", "is_super_admin": True, "permissions": ["*"]}

    app.dependency_overrides[deps.get_current_admin] = override_get_current_admin
    try:
        files = {"file": ("bad.txt", BytesIO(b"hello"), "text/plain")}
        response = await async_client.post("/api/v1/upload", files=files)
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == 400
