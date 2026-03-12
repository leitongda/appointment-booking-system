import pytest


@pytest.mark.asyncio
async def test_auth_login_rejects_invalid_credentials(async_client):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"phone": "13800138000", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == 401


@pytest.mark.asyncio
async def test_auth_refresh_rejects_invalid_token(async_client):
    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": "invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == 401
