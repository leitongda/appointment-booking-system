"""Mock 短信服务提供商（开发环境使用，打印到控制台）"""
import logging

from .provider_base import SmsProvider

logger = logging.getLogger(__name__)


class MockSmsProvider(SmsProvider):
    """Mock 短信服务提供商（开发环境使用）"""

    # 验证码有效期（秒）- 用于显示
    CODE_EXPIRE_SECONDS = 300  # 5 分钟

    async def send_verification_code(self, phone: str, code: str, code_type: str = "login") -> bool:
        """
        发送验证码（开发环境打印到控制台）

        Args:
            phone: 手机号
            code: 验证码
            code_type: 验证码类型

        Returns:
            始终返回 True
        """
        logger.info(f"[SMS Mock] 向 {phone} 发送{code_type}验证码: {code}")
        print(f"\n{'='*50}")
        print("📱 短信验证码")
        print(f"手机号: {phone}")
        print(f"验证码: {code}")
        print(f"类型: {code_type}")
        print(f"有效期: {self.CODE_EXPIRE_SECONDS // 60}分钟")
        print(f"{'='*50}\n")
        return True

    async def send_notification(self, phone: str, content: str) -> bool:
        """
        发送通知短信（开发环境打印到控制台）

        Args:
            phone: 手机号
            content: 短信内容

        Returns:
            始终返回 True
        """
        logger.info(f"[SMS Mock] 向 {phone} 发送通知: {content}")
        print(f"\n{'='*50}")
        print("📱 短信通知")
        print(f"手机号: {phone}")
        print(f"内容: {content}")
        print(f"{'='*50}\n")
        return True
