"""
登录成功场景集成测试

覆盖:
- 用户登录成功
- 管理员登录成功
- 医生登录成功
- 账号被禁用返回 403
- Token 刷新成功
"""
import bcrypt
import pytest
from datetime import datetime
from uuid import uuid4


@pytest.mark.asyncio
async def test_user_login_success(async_client, db_session, test_user):
    """用户登录成功，验证 token"""
    # 更新用户密码为已知值
    password = "test_password123"
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    test_user.password_hash = password_hash
    await db_session.commit()

    response = await async_client.post(
        "/api/v1/auth/login",
        json={"phone": test_user.phone, "password": password},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert "accessToken" in data
    assert "refreshToken" in data
    assert data["expiresIn"] > 0
    assert data["user"]["id"] == test_user.id
    assert data["user"]["phone"] == test_user.phone


@pytest.mark.asyncio
async def test_admin_login_success(async_client, db_session, test_super_admin):
    """管理员登录成功"""
    # 更新管理员密码为已知值
    password = "admin_password123"
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    test_super_admin.password_hash = password_hash
    await db_session.commit()

    response = await async_client.post(
        "/api/v1/admin/login",
        json={"username": test_super_admin.username, "password": password, "encrypted": False},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert "accessToken" in data
    assert "refreshToken" in data
    assert data["admin"]["id"] == test_super_admin.id
    assert data["admin"]["username"] == test_super_admin.username


@pytest.mark.asyncio
async def test_doctor_login_success(async_client, db_session, test_doctor):
    """医生登录成功"""
    from app.models.doctor import Doctor

    # 创建医生账号（带用户名和密码）
    password = "doctor_password123"
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    # 更新医生的登录信息
    test_doctor.password_hash = password_hash
    test_doctor.username = "testdoctor"
    await db_session.commit()

    response = await async_client.post(
        "/api/v1/doctors/login",
        json={"phone": test_doctor.username, "password": password},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["doctor"]["id"] == test_doctor.id


@pytest.mark.asyncio
async def test_login_disabled_account(async_client, db_session, test_user):
    """账号被禁用返回 403"""
    # 更新用户密码并禁用账号
    password = "test_password123"
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    test_user.password_hash = password_hash
    test_user.status = 0  # 禁用账号
    await db_session.commit()

    response = await async_client.post(
        "/api/v1/auth/login",
        json={"phone": test_user.phone, "password": password},
    )

    assert response.status_code == 403
    assert "禁用" in response.json().get("message", "")


@pytest.mark.asyncio
async def test_admin_login_disabled_account(async_client, db_session, test_super_admin):
    """管理员账号被禁用返回 403"""
    # 更新管理员密码并禁用账号
    password = "admin_password123"
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    test_super_admin.password_hash = password_hash
    test_super_admin.status = 0  # 禁用账号
    await db_session.commit()

    response = await async_client.post(
        "/api/v1/admin/login",
        json={"username": test_super_admin.username, "password": password, "encrypted": False},
    )

    assert response.status_code == 403
    assert "禁用" in response.json().get("message", "")


@pytest.mark.asyncio
async def test_token_refresh_success(async_client, db_session, test_user):
    """Token 刷新成功"""
    from app.core.security import create_refresh_token

    # 创建有效的 refresh token
    refresh_token = create_refresh_token({"sub": test_user.id})

    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert "accessToken" in data
    assert "refreshToken" in data
    assert data["expiresIn"] > 0


@pytest.mark.asyncio
async def test_admin_token_refresh_success(async_client, db_session, test_super_admin):
    """管理员 Token 刷新成功"""
    from app.core.security import create_refresh_token

    # 创建有效的 refresh token（新格式）
    refresh_token = create_refresh_token({"sub": test_super_admin.id, "type": "refresh", "role_type": "admin"})

    response = await async_client.post(
        "/api/v1/admin/refresh",
        json={"refreshToken": refresh_token},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert "accessToken" in data
    assert "refreshToken" in data
    assert data["expiresIn"] > 0


@pytest.mark.asyncio
async def test_doctor_token_refresh_success(async_client, db_session, test_doctor):
    """医生 Token 刷新成功"""
    from app.core.security import create_refresh_token

    refresh_token = create_refresh_token({"sub": test_doctor.id, "type": "refresh", "role_type": "doctor"})

    response = await async_client.post(
        "/api/v1/doctors/refresh",
        json={"refreshToken": refresh_token},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert "accessToken" in data
    assert "refreshToken" in data
    assert data["expiresIn"] > 0


@pytest.mark.asyncio
async def test_refresh_with_disabled_account(async_client, db_session, test_user):
    """使用被禁用账号的 refresh token 应返回 401"""
    from app.core.security import create_refresh_token

    # 创建 refresh token
    refresh_token = create_refresh_token({"sub": test_user.id})

    # 禁用用户
    test_user.status = 0
    await db_session.commit()

    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 401
