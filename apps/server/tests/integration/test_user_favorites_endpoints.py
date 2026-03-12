from uuid import uuid4

import pytest

from app.api import deps
from app.main import app
from app.models.department import Department
from app.models.user import User
from app.models.user_favorite import UserFavorite


@pytest.mark.asyncio
async def test_user_favorites_check_endpoint(async_client, db_session):
    user = User(
        id=str(uuid4()),
        phone="13800138019",
        password_hash="hashed",
        nickname="收藏用户",
        status=1,
    )
    department = Department(
        id=str(uuid4()),
        name="收藏科室",
        status=1,
    )
    favorite = UserFavorite(
        id=str(uuid4()),
        user_id=user.id,
        target_type="department",
        target_id=department.id,
    )
    db_session.add_all([user, department, favorite])
    await db_session.commit()

    async def override_get_current_user():
        return {"id": user.id}

    app.dependency_overrides[deps.get_current_user] = override_get_current_user
    try:
        response = await async_client.get(
            f"/api/v1/favorites/check?targetType=department&targetId={department.id}"
        )
    finally:
        app.dependency_overrides.pop(deps.get_current_user, None)

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["isFavorited"] is True
    assert payload["favoriteId"] == favorite.id
