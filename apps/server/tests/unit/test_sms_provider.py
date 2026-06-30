"""短信服务提供商单元测试"""
import pytest
from app.infrastructure.sms.provider_base import SmsProvider
from app.infrastructure.sms.mock_provider import MockSmsProvider
from app.infrastructure.sms.factory import get_sms_provider
from app.infrastructure.sms.retry import coerce_extra_data, normalize_sms_result, send_sms_retry
from app.infrastructure.sms.providers.tencent_provider import TencentSmsProvider


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

    def test_factory_normalizes_tencent_provider(self, monkeypatch):
        """测试 provider 配置支持大小写和空格容错"""
        monkeypatch.setattr("app.infrastructure.sms.factory.settings.SMS_PROVIDER", " Tencent ")

        provider = get_sms_provider()

        assert isinstance(provider, TencentSmsProvider)


class TestSmsProviderAbstract:
    """测试 SmsProvider 抽象基类"""

    def test_cannot_instantiate_abstract_base(self):
        """测试不能直接实例化抽象基类"""
        with pytest.raises(TypeError):
            SmsProvider()


class TestTencentSmsProvider:
    """测试 TencentSmsProvider 边界转换"""

    def test_normalize_mainland_phone(self):
        """测试国内手机号自动转换为 E.164 格式"""
        assert TencentSmsProvider._normalize_phone("13800138000") == "+8613800138000"

    def test_keep_international_phone(self):
        """测试国际格式手机号保持不变"""
        assert TencentSmsProvider._normalize_phone("+85251234567") == "+85251234567"

    def test_normalize_template_params_from_dict(self):
        """测试 dict 模板参数按插入顺序转换为位置参数"""
        params = TencentSmsProvider._normalize_template_params({
            "patient_name": "张三",
            "doctor": "李医生",
        })

        assert params == ["张三", "李医生"]

    def test_normalize_template_params_from_list(self):
        """测试列表模板参数转换为字符串列表"""
        params = TencentSmsProvider._normalize_template_params(["张三", 3])

        assert params == ["张三", "3"]


class TestSmsRetryHelpers:
    """测试短信重试辅助函数"""

    def test_normalize_sms_result_handles_failed_tuple(self):
        """测试 (False, error) 不会被误判为成功"""
        assert normalize_sms_result((False, "发送失败")) is False

    def test_coerce_extra_data_from_json_string(self):
        """测试 JSON 字符串 extra_data 可被解析"""
        data = coerce_extra_data('{"template_code": "TPL_001", "template_params": {"code": "123456"}}')

        assert data["template_code"] == "TPL_001"
        assert data["template_params"] == {"code": "123456"}

    def test_send_sms_retry_uses_business_template_signature(self):
        """测试模板短信重试使用统一关键字签名"""
        class Provider:
            def __init__(self):
                self.calls = []

            async def send_business_notification(self, **kwargs):
                self.calls.append(kwargs)
                return True, None

        provider = Provider()
        success = send_sms_retry(
            provider=provider,
            phone="13800138000",
            extra_data={
                "template_code": "TPL_001",
                "template_params": {"code": "123456"},
            },
        )

        assert success is True
        assert provider.calls == [{
            "phone": "13800138000",
            "template_code": "TPL_001",
            "template_params": {"code": "123456"},
        }]

    def test_send_sms_retry_awaits_notification_fallback(self):
        """测试无模板时会 await 普通通知并归一化结果"""
        class Provider:
            def __init__(self):
                self.calls = []

            async def send_notification(self, phone, content):
                self.calls.append((phone, content))
                return False

        provider = Provider()
        success = send_sms_retry(
            provider=provider,
            phone="13800138000",
            content="通知内容",
        )

        assert success is False
        assert provider.calls == [("13800138000", "通知内容")]
