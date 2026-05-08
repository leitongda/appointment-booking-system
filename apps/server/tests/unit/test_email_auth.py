"""邮箱认证功能单元测试

测试邮箱验证码、邮箱登录、邮箱绑定/解绑/换绑等功能。
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime
from fastapi import HTTPException

from app.modules.users.service import UserService
from app.schemas.user import UserCreate
from app.models.user import User
from app.models.account import Account, AccountUser
from app.core.redis import RedisCache


# ==================== UserService.get_by_email 测试 ====================

@pytest.mark.unit
class TestGetByEmail:
    """通过邮箱查询用户"""

    async def test_get_by_email_found(self, db_session, test_user):
        """通过邮箱查到已有用户"""
        test_user.email = "test@example.com"
        await db_session.flush()

        service = UserService(db_session)
        user = await service.get_by_email("test@example.com")
        assert user is not None
        assert user.id == test_user.id

    async def test_get_by_email_not_found(self, db_session):
        """查询不存在的邮箱"""
        service = UserService(db_session)
        user = await service.get_by_email("nonexist@example.com")
        assert user is None

    async def test_get_by_email_empty(self, db_session):
        """空邮箱查询返回 None"""
        service = UserService(db_session)
        assert await service.get_by_email("") is None
        assert await service.get_by_email("   ") is None
        assert await service.get_by_email(None) is None


# ==================== UserCreate with email 测试 ====================

@pytest.mark.unit
class TestUserCreateWithEmail:
    """创建带邮箱的用户"""

    async def test_create_user_with_email(self, db_session, test_tenant):
        """创建带邮箱的用户应正确保存 email 字段"""
        service = UserService(db_session)
        user = await service.create(UserCreate(
            email="new@example.com",
            password="123456",
            nickname="邮箱用户",
        ))
        assert user.email == "new@example.com"
        assert user.phone is None or user.phone == ""

    async def test_create_user_without_email(self, db_session, test_tenant):
        """创建不带邮箱的用户"""
        service = UserService(db_session)
        user = await service.create(UserCreate(
            phone="13900139000",
            password="123456",
        ))
        assert user.email is None
        assert user.phone == "13900139000"


# ==================== 邮箱验证码 Redis 操作测试 ====================

@pytest.mark.unit
class TestEmailCodeRedis:
    """邮箱验证码 Redis 存储"""

    @patch("app.core.redis.get_redis")
    async def test_set_and_get_email_code(self, mock_get_redis):
        """存储并获取邮箱验证码"""
        mock_client = AsyncMock()
        mock_client.get.return_value = '{"code": "123456", "verified": false}'
        mock_client.set.return_value = True
        mock_get_redis.return_value = mock_client

        result = await RedisCache.set_email_code("test@example.com", "123456", "login")
        assert result is True

    @patch("app.core.redis.get_redis")
    async def test_verify_email_code_success(self, mock_get_redis):
        """验证正确的邮箱验证码"""
        mock_client = AsyncMock()
        mock_client.get.return_value = '{"code": "123456", "verified": false}'
        mock_client.set.return_value = True
        mock_client.ttl.return_value = 200
        mock_get_redis.return_value = mock_client

        result = await RedisCache.verify_email_code("test@example.com", "123456", "login")
        assert result is True

    @patch("app.core.redis.get_redis")
    async def test_verify_email_code_wrong(self, mock_get_redis):
        """验证错误的邮箱验证码"""
        mock_client = AsyncMock()
        mock_client.get.return_value = '{"code": "123456", "verified": false}'
        mock_get_redis.return_value = mock_client

        result = await RedisCache.verify_email_code("test@example.com", "999999", "login")
        assert result is False

    @patch("app.core.redis.get_redis")
    async def test_verify_email_code_already_used(self, mock_get_redis):
        """验证已使用的验证码"""
        mock_client = AsyncMock()
        mock_client.get.return_value = '{"code": "123456", "verified": true}'
        mock_get_redis.return_value = mock_client

        result = await RedisCache.verify_email_code("test@example.com", "123456", "login")
        assert result is False

    @patch("app.core.redis.get_redis")
    async def test_verify_email_code_expired(self, mock_get_redis):
        """验证已过期的验证码"""
        mock_client = AsyncMock()
        mock_client.get.return_value = None
        mock_get_redis.return_value = mock_client

        result = await RedisCache.verify_email_code("test@example.com", "123456", "login")
        assert result is False

    @patch("app.core.redis.get_redis")
    async def test_check_email_rate_limit_can_send(self, mock_get_redis):
        """检查发送频率 — 可以发送"""
        mock_client = AsyncMock()
        mock_client.ttl.return_value = -2  # key 不存在
        mock_client.set.return_value = True
        mock_get_redis.return_value = mock_client

        can_send, wait = await RedisCache.check_email_rate_limit("test@example.com", "login")
        assert can_send is True
        assert wait == 0

    @patch("app.core.redis.get_redis")
    async def test_check_email_rate_limit_too_fast(self, mock_get_redis):
        """检查发送频率 — 太快"""
        mock_client = AsyncMock()
        mock_client.ttl.return_value = 30  # 还有30秒
        mock_get_redis.return_value = mock_client

        can_send, wait = await RedisCache.check_email_rate_limit("test@example.com", "login")
        assert can_send is False
        assert wait == 30


# ==================== 邮箱格式校验测试 ====================

@pytest.mark.unit
class TestEmailFormatValidation:
    """邮箱格式校验"""

    def test_valid_email(self):
        """合法邮箱格式"""
        from app.modules.auth.router import _validate_email_format
        assert _validate_email_format("user@example.com") is True
        assert _validate_email_format("test.name+tag@domain.co.uk") is True
        assert _validate_email_format("admin@hospital.cn") is True

    def test_invalid_email(self):
        """非法邮箱格式"""
        from app.modules.auth.router import _validate_email_format
        assert _validate_email_format("") is False
        assert _validate_email_format("not-an-email") is False
        assert _validate_email_format("@domain.com") is False
        assert _validate_email_format("user@") is False
        assert _validate_email_format("user@.com") is False


# ==================== 验证码安全性测试 ====================

@pytest.mark.unit
class TestCodeGenerationSecurity:
    """验证码生成安全性"""

    def test_generate_code_uses_secrets(self):
        """验证码生成使用 secrets 模块（密码学安全）"""
        from app.infrastructure.sms.service import SmsService
        import inspect
        source = inspect.getsource(SmsService.generate_code)
        assert "secrets.choice" in source
        assert "random.choices" not in source

    def test_generate_code_length(self):
        """验证码长度正确"""
        from app.infrastructure.sms.service import SmsService
        code = SmsService.generate_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_generate_code_randomness(self):
        """验证码具有随机性（连续生成 100 个不全相同）"""
        from app.infrastructure.sms.service import SmsService
        codes = {SmsService.generate_code() for _ in range(100)}
        assert len(codes) > 90  # 极高概率全部不同
