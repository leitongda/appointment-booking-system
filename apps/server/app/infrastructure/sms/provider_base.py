"""短信服务提供商抽象基类"""
from abc import ABC, abstractmethod


class SmsProvider(ABC):
    """短信服务提供商抽象基类"""

    @abstractmethod
    async def send_verification_code(self, phone: str, code: str, code_type: str = "login") -> bool:
        """
        发送验证码

        Args:
            phone: 手机号
            code: 验证码
            code_type: 验证码类型（login/register/reset）

        Returns:
            是否发送成功
        """
        pass

    @abstractmethod
    async def send_notification(self, phone: str, content: str) -> bool:
        """
        发送通知短信

        Args:
            phone: 手机号
            content: 短信内容

        Returns:
            是否发送成功
        """
        pass
