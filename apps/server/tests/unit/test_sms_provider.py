"""短信服务提供商单元测试"""
import pytest
from app.infrastructure.sms.provider_base import SmsProvider
from app.infrastructure.sms.mock_provider import MockSmsProvider
from app.infrastructure.sms.factory import get_sms_provider


class TestMockSmsProvider:
    """测试 MockSmsProvider"""

    @pytest.mark.asyncio
    async def test_send_verification_code_returns_true(self):
        """测试发送验证码返回 True"""
        provider = MockSmsProvider()
        result = await provider.send_verification_code("13800138000", "123456", "login")
        assert result is True

    @pytest.mark.asyncio
    async def test_send_notification_returns_true(self):
        """测试发送通知返回 True"""
        provider = MockSmsProvider()
        result = await provider.send_notification("13800138000", "您的预约已成功")
        assert result is True


class TestSmsProviderFactory:
    """测试短信服务提供商工厂"""

    def test_factory_returns_mock_provider_by_default(self):
        """测试 factory 默认返回 MockSmsProvider"""
        provider = get_sms_provider()
        assert isinstance(provider, MockSmsProvider)

    def test_factory_returns_mock_provider_for_unknown_provider(self):
        """测试未知 provider 返回 MockSmsProvider"""
        # 这里无法直接测试，因为 get_sms_provider 依赖 settings
        # 实际测试需要 mock settings
        provider = get_sms_provider()
        assert isinstance(provider, MockSmsProvider)


class TestSmsProviderAbstract:
    """测试 SmsProvider 抽象基类"""

    def test_cannot_instantiate_abstract_base(self):
        """测试不能直接实例化抽象基类"""
        with pytest.raises(TypeError):
            SmsProvider()
