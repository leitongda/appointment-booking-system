from io import BytesIO
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.api import deps
from app.common.auth_types import AccountInfo, RoleType, UserInfo
from app.common.auth_unified import get_current_account
from app.main import app
from app.models.admin import Admin
from app.models.doctor import Doctor
from app.models.user import User
from app.core.security import get_password_hash


@pytest.mark.asyncio
async def test_users_profile_endpoint(async_client, db_session):
    user = User(
        id=str(uuid4()),
        phone="13800138009",
        email="profile@example.com",
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
    assert payload["email"] == "profile@example.com"
    assert payload["hasPassword"] is True


@pytest.mark.asyncio
async def test_auth_account_me_endpoint(async_client):
    async def override_get_current_account():
        return AccountInfo(
            id="user-1",
            role_type=RoleType.USER,
            tenant_id="tenant-1",
            phone="13800138012",
            name="统一账号用户",
            avatar="https://example.com/avatar.png",
            status=1,
            user_info=UserInfo(openid="wx-openid", points=12, permissions=["profile:read"]),
        )

    app.dependency_overrides[get_current_account] = override_get_current_account
    try:
        response = await async_client.get("/api/v1/auth/account/me")
    finally:
        app.dependency_overrides.pop(get_current_account, None)

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["id"] == "user-1"
    assert payload["roleType"] == "user"
    assert payload["phone"] == "13800138012"
    assert payload["nickname"] == "统一账号用户"
    assert payload["openid"] == "wx-openid"
    assert payload["points"] == 12


@pytest.mark.asyncio
async def test_admin_change_password_syncs_account(async_client, db_session):
    admin = Admin(
        id=str(uuid4()),
        username="sync-admin",
        password_hash=get_password_hash("old_password123"),
        name="测试管理员",
        phone="13800138010",
        status=1,
    )
    db_session.add(admin)
    await db_session.commit()

    async def override_get_current_admin():
        return {"id": admin.id}

    sync_mock = AsyncMock()
    app.dependency_overrides[deps.get_current_admin] = override_get_current_admin
    try:
        with patch("app.modules.admin.router_auth_password.AccountSyncService.sync_admin_to_account", sync_mock):
            response = await async_client.put(
                "/api/v1/admin/me/change-password",
                json={"old_password": "old_password123", "new_password": "new_password456"},
            )
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    sync_mock.assert_awaited_once_with(db_session, admin.id, operator_id=admin.id)


@pytest.mark.asyncio
async def test_admin_email_login_endpoint(async_client, db_session):
    admin = Admin(
        id=str(uuid4()),
        username="email-admin",
        password_hash=get_password_hash("unused_password"),
        name="邮箱管理员",
        email="admin@example.com",
        phone="13800138100",
        status=1,
    )
    db_session.add(admin)
    await db_session.commit()

    verify_mock = AsyncMock(return_value=True)
    try:
        with patch("app.modules.admin.router_auth_login.RedisCache.verify_email_code", verify_mock):
            response = await async_client.post(
                "/api/v1/admin/email/login",
                json={"email": "admin@example.com", "code": "123456"},
            )
    finally:
        pass

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["admin"]["id"] == admin.id
    verify_mock.assert_awaited_once_with("admin@example.com", "123456", "admin_login")


@pytest.mark.asyncio
async def test_admin_bind_email_syncs_account(async_client, db_session):
    admin = Admin(
        id=str(uuid4()),
        username="bind-admin",
        password_hash=get_password_hash("unused_password"),
        name="绑定管理员",
        phone="13800138101",
        status=1,
    )
    db_session.add(admin)
    await db_session.commit()

    async def override_get_current_admin():
        return {"id": admin.id}

    verify_mock = AsyncMock(return_value=True)
    sync_mock = AsyncMock()
    app.dependency_overrides[deps.get_current_admin] = override_get_current_admin
    try:
        with patch("app.modules.admin.router_auth_password.RedisCache.verify_email_code", verify_mock):
            with patch("app.modules.admin.router_auth_password.AccountSyncService.sync_admin_to_account", sync_mock):
                response = await async_client.post(
                    "/api/v1/admin/me/email/bind",
                    json={"email": "bind@example.com", "code": "654321"},
                )
    finally:
        app.dependency_overrides.pop(deps.get_current_admin, None)

    assert response.status_code == 200
    await db_session.refresh(admin)
    assert admin.email == "bind@example.com"
    sync_mock.assert_awaited_once_with(db_session, admin.id, operator_id=admin.id)
    verify_mock.assert_awaited_once_with("bind@example.com", "654321", "admin_bind")


@pytest.mark.asyncio
async def test_doctor_change_password_syncs_account(async_client, db_session):
    doctor = Doctor(
        id=str(uuid4()),
        name="测试医生",
        phone="13800138011",
        username="doctor-sync",
        password_hash=get_password_hash("old_password123"),
        department_id=str(uuid4()),
        store_id=str(uuid4()),
        status=1,
    )
    db_session.add(doctor)
    await db_session.commit()

    async def override_get_current_doctor():
        return doctor

    sync_mock = AsyncMock()
    app.dependency_overrides[deps.get_current_doctor_by_token] = override_get_current_doctor
    try:
        with patch("app.modules.doctors.router.AccountSyncService.sync_doctor_to_account", sync_mock):
            response = await async_client.post(
                "/api/v1/doctors/change-password",
                json={"old_password": "old_password123", "new_password": "new_password456"},
            )
    finally:
        app.dependency_overrides.pop(deps.get_current_doctor_by_token, None)

    assert response.status_code == 200
    sync_mock.assert_awaited_once_with(db_session, doctor.id, operator_id=doctor.id)


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
