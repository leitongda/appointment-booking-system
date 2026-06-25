"""企业微信通知渠道适配器。

通过 WecomProvider 发送：
- 应用消息（点对点，支持 @）
- 群机器人消息（降级）
"""
from app.infrastructure.notifications.channels.integration_base import BaseIntegrationChannel


class WecomChannel(BaseIntegrationChannel):
    """企业微信通知渠道。"""

    provider_name = "wecom"
