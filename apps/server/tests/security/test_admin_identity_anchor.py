"""P1-1：管理员平台特权判定必须锚定平台级角色（role.tenant_id IS NULL）

背景：原判定仅比对角色编码/名称字符串，租户内自建 code="SUPER_ADMIN" 的角色
即可获得平台特权。本文件锁定修复后的不变量。
"""
import json
from datetime import datetime
from uuid import uuid4

import bcrypt
import pytest
from fastapi import HTTPException

from app.common.auth_unified import _get_admin_account
from app.common.tenant_deps import get_tenant_filter
from app.middleware.tenant_context import clear_tenant_context
from app.models.admin import Admin, Role

pytestmark = [pytest.mark.security]


async def _create_role(db_session, tenant_id: str | None, code: str, name: str = "测试角色") -> Role:
    role = Role(
        id=str(uuid4()),
        name=name,
        code=code,
        description="测试角色",
        tenant_id=tenant_id,
        status=1,
        permissions=json.dumps(["*"]),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    return role


async def _create_admin(db_session, role: Role, tenant_id: str | None) -> Admin:
    admin = Admin(
        id=str(uuid4()),
        username=f"identity_{uuid4().hex[:8]}",
        password_hash=bcrypt.hashpw("password123".encode(), bcrypt.gensalt()).decode(),
        name="身份判定测试管理员",
        phone=f"136{uuid4().int % 10**8:08d}",
        role_id=role.id,
        current_store_id=None,
        tenant_id=tenant_id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


class TestPlatformPrivilegeAnchor:
    """平台特权只属于平台级角色"""

    async def test_platform_super_admin_is_privileged(self, db_session, multi_tenant_env):
        account = await _get_admin_account(
            multi_tenant_env.platform_admin.id,
            db_session,
            token="test-token",
            check_token_blacklist=False,
        )
        assert account.admin_info.is_super_admin is True
        assert account.admin_info.is_platform_admin is True
        assert account.admin_info.permissions == ["*"]
        assert get_tenant_filter(account.to_dict()) is None

    async def test_tenant_scoped_super_admin_code_is_not_privileged(
        self, db_session, multi_tenant_env
    ):
        """租户内自建 SUPER_ADMIN 角色不得获得平台特权（P0 提权链的核心不变量）"""
        env = multi_tenant_env
        role = await _create_role(
            db_session, env.tenant_a.id, "SUPER_ADMIN", name="超级管理员"
        )
        admin = await _create_admin(db_session, role, env.tenant_a.id)
        try:
            account = await _get_admin_account(
                admin.id,
                db_session,
                token="test-token",
                check_tenant=False,
                check_token_blacklist=False,
            )
            assert account.admin_info.is_super_admin is False
            assert account.admin_info.is_platform_admin is False
            # 非超管：租户过滤必须收敛到本租户，而不是 None（全平台）
            assert get_tenant_filter(account.to_dict()) == env.tenant_a.id
        finally:
            clear_tenant_context()

    async def test_platform_admin_code_on_tenant_role_is_not_platform_admin(
        self, db_session, multi_tenant_env
    ):
        """角色名/编码相同也不能绕过租户归属前提"""
        env = multi_tenant_env
        role = await _create_role(
            db_session, env.tenant_b.id, "PLATFORM_ADMIN", name="平台管理员"
        )
        admin = await _create_admin(db_session, role, env.tenant_b.id)
        try:
            account = await _get_admin_account(
                admin.id,
                db_session,
                token="test-token",
                check_tenant=False,
                check_token_blacklist=False,
            )
            assert account.admin_info.is_platform_admin is False
            assert account.admin_info.is_super_admin is False
        finally:
            clear_tenant_context()

    async def test_tenant_admin_keeps_tenant_filter(self, db_session, multi_tenant_env):
        env = multi_tenant_env
        account = await _get_admin_account(
            env.admin_a.id,
            db_session,
            token="test-token",
            check_tenant=False,
            check_token_blacklist=False,
        )
        try:
            assert account.admin_info.is_super_admin is False
            assert get_tenant_filter(account.to_dict()) == env.tenant_a.id
        finally:
            clear_tenant_context()


class TestLegacyUserFallback:
    """遗留 User 表管理员兼容开关（LEGACY_USER_ADMIN_FALLBACK）"""

    async def test_disabled_returns_401(self, db_session, test_user, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "LEGACY_USER_ADMIN_FALLBACK", False)
        with pytest.raises(HTTPException) as exc_info:
            await _get_admin_account(
                test_user.id,
                db_session,
                token="test-token",
                check_token_blacklist=False,
            )
        assert exc_info.value.status_code == 401

    async def test_enabled_preserves_legacy_behavior(self, db_session, test_user, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "LEGACY_USER_ADMIN_FALLBACK", True)
        account = await _get_admin_account(
            test_user.id,
            db_session,
            token="test-token",
            check_token_blacklist=False,
        )
        assert account.admin_info.is_super_admin is True
        assert account.admin_info.permissions == ["*"]
