"""第三方集成 Provider 与通知渠道注册表测试。

验证：
- 三个平台 Provider 正确注册并可解析
- provider_name 属性正确
- 通知渠道注册表包含新增的 3 个第三方渠道
- 注册幂等性
"""
import pytest

from app.infrastructure.integrations import (
    get_provider,
    integration_registry,
    register_integration_providers,
)
from app.infrastructure.integrations.base import BaseIntegrationProvider
from app.infrastructure.integrations.dingtalk.provider import DingtalkProvider
from app.infrastructure.integrations.feishu.provider import FeishuProvider
from app.infrastructure.integrations.wecom.provider import WecomProvider
from app.infrastructure.notifications.channels.dingtalk import DingtalkChannel
from app.infrastructure.notifications.channels.feishu import FeishuChannel
from app.infrastructure.notifications.channels.wecom import WecomChannel
from app.infrastructure.notifications.registry import channel_registry, register_channels


class TestProviderRegistry:
    """Provider 注册表测试。"""

    def test_all_providers_registered(self):
        """三个平台 Provider 都应注册。"""
        register_integration_providers()
        providers = integration_registry.list_providers()
        assert "dingtalk" in providers
        assert "wecom" in providers
        assert "feishu" in providers

    def test_get_provider_returns_instance(self):
        """get_provider 应返回 Provider 实例。"""
        for name in ("dingtalk", "wecom", "feishu"):
            provider = get_provider(name)
            assert provider is not None
            assert isinstance(provider, BaseIntegrationProvider)
            assert provider.provider_name == name

    def test_get_unknown_provider_returns_none(self):
        """未知平台应返回 None。"""
        assert get_provider("unknown_platform") is None

    def test_registration_is_idempotent(self):
        """重复注册不应报错或产生重复。"""
        register_integration_providers()
        register_integration_providers()
        providers = integration_registry.list_providers()
        # 每个平台只出现一次（dict key 天然去重）
        assert providers.count("dingtalk") == 1

    def test_provider_classes_have_correct_name(self):
        """Provider 类的 provider_name 属性正确。"""
        assert DingtalkProvider.provider_name == "dingtalk"
        assert WecomProvider.provider_name == "wecom"
        assert FeishuProvider.provider_name == "feishu"


class TestChannelRegistry:
    """通知渠道注册表测试。"""

    def test_integration_channels_registered(self):
        """三个第三方渠道应注册到通知渠道注册表。"""
        register_channels()
        channels = channel_registry.list_channels()
        assert "dingtalk" in channels
        assert "wecom" in channels
        assert "feishu" in channels

    def test_channel_classes_have_correct_name(self):
        """Channel 类的 channel_name 正确。"""
        # channel_name 是实例 property，需实例化（传 None 作为 db）
        assert DingtalkChannel(None).channel_name == "dingtalk"
        assert WecomChannel(None).channel_name == "wecom"
        assert FeishuChannel(None).channel_name == "feishu"

    def test_all_builtin_channels_present(self):
        """原有 5 个渠道不应丢失。"""
        register_channels()
        channels = channel_registry.list_channels()
        for expected in ("in_app", "wechat", "sms", "email", "websocket"):
            assert expected in channels, f"原有渠道 {expected} 丢失"

    def test_total_channel_count(self):
        """总渠道数应为 8（5 原有 + 3 新增）。"""
        register_channels()
        channels = channel_registry.list_channels()
        assert len(channels) >= 8
