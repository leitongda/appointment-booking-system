"""第三方集成 Provider 注册表。

仿 notifications/channel_registry 模式：全局单例 + register/get 方法。
业务代码面向 BaseIntegrationProvider 接口编程，通过 provider_name 获取具体实现。
"""
from __future__ import annotations

import logging

from app.infrastructure.integrations.base import BaseIntegrationProvider

logger = logging.getLogger(__name__)


class IntegrationProviderRegistry:
    """第三方集成 Provider 注册表。"""

    def __init__(self) -> None:
        self._providers: dict[str, type[BaseIntegrationProvider]] = {}

    def register(self, provider_class: type[BaseIntegrationProvider]) -> None:
        """注册 Provider 类（以 provider_name 为键）。"""
        name = provider_class.provider_name
        self._providers[name] = provider_class
        logger.info("[集成注册表] 注册 Provider: %s", name)

    def get(self, provider_name: str) -> BaseIntegrationProvider | None:
        """获取 Provider 实例（每次新建，无状态）。"""
        cls = self._providers.get(provider_name)
        return cls() if cls else None

    def list_providers(self) -> list[str]:
        """列出所有已注册平台。"""
        return list(self._providers.keys())

    def is_available(self, provider_name: str) -> bool:
        return provider_name in self._providers


# 全局注册表实例
integration_registry = IntegrationProviderRegistry()


def register_integration_providers() -> None:
    """注册所有内置第三方平台 Provider。

    幂等：重复调用安全。
    """
    from app.infrastructure.integrations.dingtalk.provider import DingtalkProvider
    from app.infrastructure.integrations.feishu.provider import FeishuProvider
    from app.infrastructure.integrations.wecom.provider import WecomProvider

    for cls in (DingtalkProvider, WecomProvider, FeishuProvider):
        if cls.provider_name not in integration_registry._providers:
            integration_registry.register(cls)


def get_provider(provider_name: str) -> BaseIntegrationProvider | None:
    """获取 Provider 实例（首次调用自动注册，对外便捷入口）。"""
    if not integration_registry._providers:
        register_integration_providers()
    return integration_registry.get(provider_name)
