from io import BytesIO
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.api import deps
from app.common.auth_types import AccountInfo, RoleType, UserInfo
from app.common.auth_unified import get_current_account
from app.main import app
from app.models.account import Account
from app.models.admin import Admin
from app.models.doctor import Doctor
from app.models.user import User
from app.core.security import get_password_hash, verify_password


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
async def test_accounts_me_endpoint(async_client):
    async def override_get_current_account():
        return AccountInfo(
            id="doctor-1",
            role_type=RoleType.DOCTOR,
            tenant_id="tenant-1",
            phone="13800138066",
            name="统一账号医生",
            avatar="https://example.com/doctor.png",
            status=1,
        )

    app.dependency_overrides[get_current_account] = override_get_current_account
    try:
        response = await async_client.get("/api/v1/accounts/me")
    finally:
        app.dependency_overrides.pop(get_current_account, None)

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["id"] == "doctor-1"
    assert payload["roleType"] == "doctor"
    assert payload["name"] == "统一账号医生"


@pytest.mark.asyncio
async def test_accounts_change_password_syncs_user_legacy(async_client, db_session, test_tenant):
    user_id = str(uuid4())
    old_password = "old_password123"
    new_password = "new_password456"
    old_hash = get_password_hash(old_password)

    user = User(
        id=user_id,
        tenant_id=test_tenant.id,
        phone="13800138601",
        password_hash=old_hash,
        nickname="账号用户",
        status=1,
    )
    account = Account(
        id=user_id,
        tenant_id=test_tenant.id,
        phone="13800138601",
        password_hash=old_hash,
        nickname="账号用户",
        name="账号用户",
        status=1,
    )
    db_session.add(user)
    db_session.add(account)
    await db_session.commit()

    async def override_get_current_account():
        return AccountInfo(
            id=user_id,
            role_type=RoleType.USER,
            tenant_id=test_tenant.id,
            phone=user.phone,
            name=user.nickname,
            status=1,
        )

    app.dependency_overrides[get_current_account] = override_get_current_account
    try:
        response = await async_client.post(
            "/api/v1/accounts/me/change-password",
            json={"old_password": old_password, "new_password": new_password},
        )
    finally:
        app.dependency_overrides.pop(get_current_account, None)

    assert response.status_code == 200
    await db_session.refresh(user)
    await db_session.refresh(account)
    assert verify_password(new_password, user.password_hash)
    assert verify_password(new_password, account.password_hash)


@pytest.mark.asyncio
async def test_accounts_change_password_syncs_admin_legacy(async_client, db_session, test_tenant):
    admin_id = str(uuid4())
    old_password = "old_password123"
    new_password = "new_password456"
    old_hash = get_password_hash(old_password)

    admin = Admin(
        id=admin_id,
        username="account-admin",
        password_hash=old_hash,
        name="账号管理员",
        phone="13800138602",
        tenant_id=test_tenant.id,
        status=1,
    )
    account = Account(
        id=admin_id,
        tenant_id=test_tenant.id,
        phone="13800138602",
        username="account-admin",
        password_hash=old_hash,
        nickname="账号管理员",
        name="账号管理员",
        status=1,
    )
    db_session.add(admin)
    db_session.add(account)
    await db_session.commit()

    async def override_get_current_account():
        return AccountInfo(
            id=admin_id,
            role_type=RoleType.ADMIN,
            tenant_id=test_tenant.id,
            phone=admin.phone,
            name=admin.name,
            status=1,
        )

    app.dependency_overrides[get_current_account] = override_get_current_account
    try:
        response = await async_client.post(
            "/api/v1/accounts/me/change-password",
            json={"old_password": old_password, "new_password": new_password},
        )
    finally:
        app.dependency_overrides.pop(get_current_account, None)

    assert response.status_code == 200
    await db_session.refresh(admin)
    await db_session.refresh(account)
    assert verify_password(new_password, admin.password_hash)
    assert verify_password(new_password, account.password_hash)


@pytest.mark.asyncio
async def test_accounts_change_password_syncs_doctor_legacy(async_client, db_session, test_tenant):
    doctor_id = str(uuid4())
    old_password = "old_password123"
    new_password = "new_password456"
    old_hash = get_password_hash(old_password)

    doctor = Doctor(
        id=doctor_id,
        tenant_id=test_tenant.id,
        name="账号医生",
        phone="13800138603",
        username="account-doctor",
        password_hash=old_hash,
        department_id=str(uuid4()),
        store_id=str(uuid4()),
        status=1,
    )
    account = Account(
        id=doctor_id,
        tenant_id=test_tenant.id,
        phone="13800138603",
        username="account-doctor",
        password_hash=old_hash,
        nickname="账号医生",
        name="账号医生",
        status=1,
    )
    db_session.add(doctor)
    db_session.add(account)
    await db_session.commit()

    async def override_get_current_account():
        return AccountInfo(
            id=doctor_id,
            role_type=RoleType.DOCTOR,
            tenant_id=test_tenant.id,
            phone=doctor.phone,
            name=doctor.name,
            status=1,
        )

    app.dependency_overrides[get_current_account] = override_get_current_account
    try:
        response = await async_client.post(
            "/api/v1/accounts/me/change-password",
            json={"old_password": old_password, "new_password": new_password},
        )
    finally:
        app.dependency_overrides.pop(get_current_account, None)

    assert response.status_code == 200
    await db_session.refresh(doctor)
    await db_session.refresh(account)
    assert verify_password(new_password, doctor.password_hash)
    assert verify_password(new_password, account.password_hash)


@pytest.mark.asyncio
async def test_accounts_email_bind_syncs_user_legacy(async_client, db_session, test_tenant):
    user_id = str(uuid4())
    user = User(
        id=user_id,
        tenant_id=test_tenant.id,
        phone="13800138604",
        password_hash=get_password_hash("old_password123"),
        nickname="邮箱用户",
        status=1,
    )
    account = Account(
        id=user_id,
        tenant_id=test_tenant.id,
        phone="13800138604",
        password_hash=get_password_hash("old_password123"),
        nickname="邮箱用户",
        name="邮箱用户",
        status=1,
    )
    db_session.add(user)
    db_session.add(account)
    await db_session.commit()

    async def override_get_current_account():
        return AccountInfo(
            id=user_id,
            role_type=RoleType.USER,
            tenant_id=test_tenant.id,
            phone=user.phone,
            name=user.nickname,
            status=1,
        )

    verify_mock = AsyncMock(return_value=True)
    app.dependency_overrides[get_current_account] = override_get_current_account
    try:
        with patch("app.modules.accounts.router.RedisCache.verify_email_code", verify_mock):
            response = await async_client.post(
                "/api/v1/accounts/me/email/bind",
                json={"email": "account-user@example.com", "code": "123456"},
            )
    finally:
        app.dependency_overrides.pop(get_current_account, None)

    assert response.status_code == 200
    await db_session.refresh(user)
    await db_session.refresh(account)
    assert user.email == "account-user@example.com"
    assert account.email == "account-user@example.com"


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
