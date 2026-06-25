"""飞书通知渠道适配器。

通过 FeishuProvider 发送：
- 企业应用消息（点对点，支持 @）
- 群机器人消息（降级）
"""
from app.infrastructure.notifications.channels.integration_base import BaseIntegrationChannel


class FeishuChannel(BaseIntegrationChannel):
    """飞书通知渠道。"""

    provider_name = "feishu"
