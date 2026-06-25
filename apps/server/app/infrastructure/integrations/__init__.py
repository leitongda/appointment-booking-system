"""第三方集成基础设施层。

提供钉钉 / 企业微信 / 飞书 的统一能力抽象与实现：
- base.BaseIntegrationProvider: 抽象基类
- registry.integration_registry: Provider 注册表
- dingtalk/wecom/feishu: 各平台具体实现
"""
from app.infrastructure.integrations.registry import (
    get_provider,
    integration_registry,
    register_integration_providers,
)

__all__ = ["integration_registry", "register_integration_providers", "get_provider"]
