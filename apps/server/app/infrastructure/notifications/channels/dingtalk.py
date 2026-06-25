"""钉钉通知渠道适配器。

通过 DingtalkProvider 发送：
- 企业应用工作通知（点对点，支持 @）
- 群机器人消息（降级）
"""
from app.infrastructure.notifications.channels.integration_base import BaseIntegrationChannel


class DingtalkChannel(BaseIntegrationChannel):
    """钉钉通知渠道。"""

    provider_name = "dingtalk"
