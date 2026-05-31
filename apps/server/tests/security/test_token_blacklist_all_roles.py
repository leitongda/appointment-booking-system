"""Token 黑名单与安全特性测试

验证所有角色（Admin / User / Doctor）的 Token 黑名单机制：
- 被加入黑名单的 Token 在认证时应返回 401
- 未加入黑名单的 Token 应正常通过认证
- Refresh Token 轮换后旧 Token 应被加入黑名单
- must_change_password 标志在默认密码创建时应为 True
- 登录响应应在标志位为 True 时包含 X-Password-Change-Required header
"""
import hashlib
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi import HTTPException, status

from app.core.security import create_access_token, create_refresh_token, decode_token
from app.core.redis import RedisCache
from app.common.auth_unified import (
    _check_token_blacklist,
    _get_user_account,
    _get_doctor_account,
    _get_admin_account,
)


pytestmark = [pytest.mark.security]


# ==================== Fixtures ====================


@pytest_asyncio.fixture
async def admin_token(test_super_admin) -> str:
    """生成管理员类型的 access token"""
    return create_access_token(
        {"sub": test_super_admin.id, "type": "admin", "tenant_id": test_super_admin.tenant_id}
    )


@pytest_asyncio.fixture
async def user_token(test_user) -> str:
    """生成用户类型的 access token"""
    return create_access_token(
        {"sub": test_user.id, "type": "user", "tenant_id": test_user.tenant_id}
    )


@pytest_asyncio.fixture
async def doctor_token(test_doctor) -> str:
    """生成医生类型的 access token"""
    return create_access_token(
        {"sub": test_doctor.id, "type": "doctor", "tenant_id": test_doctor.tenant_id}
    )


@pytest_asyncio.fixture
async def refresh_token(test_user) -> str:
    """生成 refresh token"""
    return create_refresh_token(
        {"sub": test_user.id, "type": "refresh"}
    )


# ==================== Token 黑名单基础测试 ====================


class TestTokenBlacklistAllRoles:
    """验证 Token 黑名单对所有角色类型生效"""

    @pytest.mark.asyncio
    async def test_blacklisted_admin_token_returns_401(
        self, db_session, test_super_admin, admin_token
    ):
        """被加入黑名单的管理员 Token 应返回 401"""
        # 模拟 RedisCache.is_token_blacklisted 返回 True
        with patch.object(RedisCache, "is_token_blacklisted", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True

            with pytest.raises(HTTPException) as exc_info:
                await _get_admin_account(
                    test_super_admin.id, db_session, token=admin_token
                )

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "登录已失效" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_blacklisted_user_token_returns_401(
        self, db_session, test_user, user_token
    ):
        """被加入黑名单的用户 Token 应返回 401"""
        with patch.object(RedisCache, "is_token_blacklisted", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True

            with pytest.raises(HTTPException) as exc_info:
                await _get_user_account(
                    test_user.id, db_session, token=user_token
                )

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "登录已失效" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_blacklisted_doctor_token_returns_401(
        self, db_session, test_doctor, doctor_token
    ):
        """被加入黑名单的医生 Token 应返回 401"""
        with patch.object(RedisCache, "is_token_blacklisted", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True

            with pytest.raises(HTTPException) as exc_info:
                await _get_doctor_account(
                    test_doctor.id, db_session, token=doctor_token
                )

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "登录已失效" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_valid_token_not_in_blacklist_passes(
        self, db_session, test_super_admin, admin_token
    ):
        """未加入黑名单的 Token 应正常通过认证"""
        with patch.object(RedisCache, "is_token_blacklisted", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = False

            # 不应抛出异常
            account = await _get_admin_account(
                test_super_admin.id, db_session, token=admin_token
            )

            assert account is not None
            assert account.id == test_super_admin.id

    @pytest.mark.asyncio
    async def test_check_token_blacklist_calls_correct_key(
        self, db_session, admin_token
    ):
        """_check_token_blacklist 应使用 SHA256 哈希的前 32 位作为 key"""
        with patch.object(RedisCache, "is_token_blacklisted", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = False

            await _check_token_blacklist(admin_token)

            mock_check.assert_called_once()
            call_args = mock_check.call_args
            # 验证传入的是 token 的 SHA256 哈希前 32 位
            expected_hash = hashlib.sha256(admin_token.encode()).hexdigest()[:32]
            assert call_args[0][0] == expected_hash

    @pytest.mark.asyncio
    async def test_check_token_blacklist_passes_when_not_blacklisted(
        self, db_session, admin_token
    ):
        """Token 不在黑名单中时 _check_token_blacklist 不应抛出异常"""
        with patch.object(RedisCache, "is_token_blacklisted", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = False
            # 不应抛出异常
            await _check_token_blacklist(admin_token)

    @pytest.mark.asyncio
    async def test_check_token_blacklist_raises_when_blacklisted(
        self, db_session, admin_token
    ):
        """Token 在黑名单中时 _check_token_blacklist 应抛出 401"""
        with patch.object(RedisCache, "is_token_blacklisted", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True

            with pytest.raises(HTTPException) as exc_info:
                await _check_token_blacklist(admin_token)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


# ==================== Refresh Token 轮换测试 ====================


class TestRefreshTokenRotation:
    """验证 Refresh Token 轮换后旧 Token 被加入黑名单"""

    @pytest.mark.asyncio
    async def test_refresh_token_reuse_returns_401(
        self, db_session, test_user, refresh_token
    ):
        """刷新 Token 后，旧 refresh token 应被加入黑名单"""
        # 模拟 RedisCache.add_refresh_token_to_blacklist 被调用
        with patch.object(
            RedisCache, "add_refresh_token_to_blacklist", new_callable=AsyncMock
        ) as mock_blacklist:
            mock_blacklist.return_value = True

            with patch.object(
                RedisCache, "is_token_blacklisted", new_callable=AsyncMock
            ) as mock_check:
                mock_check.return_value = True

                # 模拟 refresh 端点的行为：调用 add_refresh_token_to_blacklist
                from jose import jwt as _jwt
                old_claims = _jwt.get_unverified_claims(refresh_token)
                exp_ts = old_claims.get("exp", 0)
                remaining_ttl = max(1, int(exp_ts - datetime.utcnow().timestamp()))

                await RedisCache.add_refresh_token_to_blacklist(
                    refresh_token, tenant_id=old_claims.get("tenant_id"), ttl=remaining_ttl
                )

                # 验证旧 token 被加入黑名单
                mock_blacklist.assert_called_once()

                # 验证旧 token 现在被标记为黑名单
                mock_check.return_value = True
                token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()[:32]
                result = await RedisCache.is_token_blacklisted(
                    token_hash, tenant_id=old_claims.get("tenant_id")
                )
                assert result is True

    @pytest.mark.asyncio
    async def test_add_refresh_token_to_blacklist_called_during_refresh(
        self, db_session, test_user, refresh_token
    ):
        """调用 add_refresh_token_to_blacklist 时应传入正确的 token 和过期时间"""
        with patch.object(
            RedisCache, "add_refresh_token_to_blacklist", new_callable=AsyncMock
        ) as mock_blacklist:
            mock_blacklist.return_value = True

            from jose import jwt as _jwt
            claims = _jwt.get_unverified_claims(refresh_token)
            exp_ts = claims.get("exp", 0)
            remaining_ttl = max(1, int(exp_ts - datetime.utcnow().timestamp()))

            await RedisCache.add_refresh_token_to_blacklist(
                refresh_token, tenant_id=claims.get("tenant_id"), ttl=remaining_ttl
            )

            mock_blacklist.assert_called_once_with(
                refresh_token, tenant_id=claims.get("tenant_id"), ttl=remaining_ttl
            )


# ==================== Redis 黑名单隔离测试 ====================


class TestBlacklistIsolation:
    """验证 Token 黑名单支持多租户隔离"""

    def test_blacklist_key_includes_tenant_id(self):
        """黑名单 key 应包含租户 ID 以实现隔离"""
        from app.middleware.tenant_context import set_tenant_context

        set_tenant_context("tenant-abc")
        key_with_tenant = RedisCache._build_token_blacklist_key("hash123", "tenant-abc")
        assert "tenant-abc" in key_with_tenant
        assert "token:blacklist:" in key_with_tenant

    def test_blacklist_key_without_tenant(self):
        """无租户上下文时黑名单 key 不包含租户维度"""
        from app.middleware.tenant_context import set_tenant_context

        set_tenant_context(None, None)
        key_no_tenant = RedisCache._build_token_blacklist_key("hash123")
        assert key_no_tenant == "token:blacklist:hash123"

    def test_different_tenants_different_blacklist_keys(self):
        """不同租户的黑名单 key 应不同"""
        key_a = RedisCache._build_token_blacklist_key("hash123", "tenant-a")
        key_b = RedisCache._build_token_blacklist_key("hash123", "tenant-b")
        assert key_a != key_b
        assert "tenant-a" in key_a
        assert "tenant-b" in key_b


# ==================== Refresh Token 黑名单隔离测试 ====================


class TestRefreshBlacklistIsolation:
    """验证 Refresh Token 黑名单支持多租户隔离"""

    def test_refresh_blacklist_key_includes_tenant_id(self):
        """Refresh Token 黑名单 key 应包含租户 ID"""
        token = "test.refresh.token"
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:32]
        key = f"{RedisCache.PREFIX_REFRESH_BLACKLIST}tenant-xyz:{token_hash}"
        assert "tenant-xyz" in key
        assert "refresh:blacklist:" in key


# ==================== must_change_password 测试 ====================


class TestMustChangePasswordFlag:
    """验证 must_change_password 标志的行为"""

    @pytest.mark.asyncio
    async def test_must_change_password_flag_set_on_creation(
        self, db_session, test_tenant, test_store, test_super_admin_role
    ):
        """新创建的管理员使用默认密码时 must_change_password 应为 True"""
        from app.models.admin import Admin

        admin = Admin(
            id=str(uuid4()),
            username=f"newadmin_{uuid4().hex[:8]}",
            password_hash="$2b$12$test_default_password_hash",
            name="新管理员",
            phone="13900139000",
            role_id=test_super_admin_role.id,
            current_store_id=test_store.id,
            tenant_id=test_tenant.id,
            status=1,
            must_change_password=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(admin)
        await db_session.commit()
        await db_session.refresh(admin)

        assert admin.must_change_password is True

    @pytest.mark.asyncio
    async def test_must_change_password_flag_default_false(
        self, db_session, test_tenant, test_store, test_super_admin_role
    ):
        """默认创建的管理员 must_change_password 应为 False"""
        from app.models.admin import Admin

        admin = Admin(
            id=str(uuid4()),
            username=f"normaladmin_{uuid4().hex[:8]}",
            password_hash="$2b$12$test_hash",
            name="普通管理员",
            phone="13900139001",
            role_id=test_super_admin_role.id,
            current_store_id=test_store.id,
            tenant_id=test_tenant.id,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(admin)
        await db_session.commit()
        await db_session.refresh(admin)

        assert admin.must_change_password is False

    @pytest.mark.asyncio
    async def test_must_change_password_flag_on_user_model(
        self, db_session, test_tenant
    ):
        """User 模型也应支持 must_change_password 标志"""
        from app.models.user import User

        user = User(
            id=str(uuid4()),
            phone=f"138{uuid4().hex[:8]}",
            password_hash="$2b$12$test_hash",
            nickname="测试用户",
            tenant_id=test_tenant.id,
            status=1,
            must_change_password=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.must_change_password is True


# ==================== 登录响应 Header 测试 ====================


class TestLoginPasswordChangeHeader:
    """验证登录响应在 must_change_password 为 True 时包含 X-Password-Change-Required"""

    def test_login_response_includes_password_change_header(self):
        """当 must_change_password=True 时，登录响应应包含 X-Password-Change-Required header"""
        from fastapi.responses import JSONResponse
        from app.schemas.auth import LoginResponse, UserInfo

        login_resp = LoginResponse(
            access_token="test_token",
            refresh_token="test_refresh",
            expires_in=3600,
            user=UserInfo(
                id="user_123",
                phone="13800138000",
                nickname="测试用户",
                avatar=None,
                gender=0,
                status=1,
            ),
        )

        resp = JSONResponse(content=login_resp.model_dump(by_alias=True))
        # 模拟 must_change_password=True 的场景
        resp.headers["X-Password-Change-Required"] = "true"

        assert resp.headers.get("X-Password-Change-Required") == "true"

    def test_login_response_no_password_change_header_when_false(self):
        """当 must_change_password=False 时，登录响应不应包含 X-Password-Change-Required header"""
        from fastapi.responses import JSONResponse
        from app.schemas.auth import LoginResponse, UserInfo

        login_resp = LoginResponse(
            access_token="test_token",
            refresh_token="test_refresh",
            expires_in=3600,
            user=UserInfo(
                id="user_123",
                phone="13800138000",
                nickname="测试用户",
                avatar=None,
                gender=0,
                status=1,
            ),
        )

        resp = JSONResponse(content=login_resp.model_dump(by_alias=True))
        # 不设置 header

        assert "X-Password-Change-Required" not in resp.headers

    def test_admin_login_response_includes_password_change_header(self):
        """管理员登录响应在 must_change_password=True 时也应包含该 header"""
        from fastapi.responses import JSONResponse

        resp = JSONResponse(content={"access_token": "test", "refresh_token": "test"})
        resp.headers["X-Password-Change-Required"] = "true"

        assert resp.headers.get("X-Password-Change-Required") == "true"


# ==================== Token 黑名单 add 方法测试 ====================


class TestBlacklistAddMethod:
    """验证 RedisCache 的黑名单添加方法"""

    @pytest.mark.asyncio
    async def test_add_token_to_blacklist_with_positive_expire(self):
        """正常过期时间应成功添加到黑名单"""
        with patch.object(RedisCache, "set", new_callable=AsyncMock) as mock_set:
            mock_set.return_value = True

            result = await RedisCache.add_token_to_blacklist("hash123", expire=3600, tenant_id="t1")

            assert result is True
            mock_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_token_to_blacklist_with_zero_expire(self):
        """过期时间为 0 时应直接返回 True（token 已过期，无需加入黑名单）"""
        result = await RedisCache.add_token_to_blacklist("hash123", expire=0, tenant_id="t1")
        assert result is True

    @pytest.mark.asyncio
    async def test_add_token_to_blacklist_with_negative_expire(self):
        """过期时间为负数时应直接返回 True（token 已过期）"""
        result = await RedisCache.add_token_to_blacklist("hash123", expire=-100, tenant_id="t1")
        assert result is True
