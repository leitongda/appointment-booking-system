"""短信服务提供商工厂"""
from app.core.config import settings
from .provider_base import SmsProvider
from .mock_provider import MockSmsProvider


def get_sms_provider() -> SmsProvider:
    """
    获取当前配置的短信服务提供商

    Returns:
        SmsProvider 实例
    """
    provider = getattr(settings, 'SMS_PROVIDER', 'mock') or 'mock'

    if provider == 'mock':
        return MockSmsProvider()
    elif provider == 'aliyun':
        from .providers.aliyun_provider import AliyunSmsProvider
        return AliyunSmsProvider()
    elif provider == 'tencent':
        # TODO: 实现 TencentSmsProvider
        # from .tencent_provider import TencentSmsProvider
        # return TencentSmsProvider()
        return MockSmsProvider()

    # 未知 provider 默认使用 mock
    return MockSmsProvider()
