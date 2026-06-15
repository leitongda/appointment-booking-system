"""阿里云短信服务提供商"""
import json
import logging

from alibabacloud_dysmsapi20170525 import models as dysms_models
from alibabacloud_dysmsapi20170525.client import Client as DysmsClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

from app.core.config import settings

from ..provider_base import SmsProvider

logger = logging.getLogger(__name__)


class AliyunSmsProvider(SmsProvider):
    """阿里云短信服务提供商"""

    def __init__(self):
        self._client: DysmsClient | None = None
        self._sign_name: str | None = None

    @property
    def client(self) -> DysmsClient:
        """懒加载阿里云 SMS 客户端"""
        if self._client is None:
            config = open_api_models.Config(
                access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
                access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET,
            )
            config.endpoint = "dysmsapi.aliyuncs.com"
            self._client = DysmsClient(config)
        return self._client

    @property
    def sign_name(self) -> str:
        """获取短信签名"""
        if self._sign_name is None:
            self._sign_name = settings.SMS_SIGN_NAME or ""
        return self._sign_name

    async def _send_sms(
        self,
        phone: str,
        template_code: str,
        template_params: dict[str, str],
    ) -> tuple[bool, str | None]:
        """
        发送短信（内部方法）

        Args:
            phone: 手机号
            template_code: 模板代码
            template_params: 模板参数

        Returns:
            (是否成功, 错误信息)
        """
        import asyncio


        try:
            request = dysms_models.SendSmsRequest(
                phone_numbers=phone,
                sign_name=self.sign_name,
                template_code=template_code,
                template_param=json.dumps(template_params) if template_params else None,
            )

            runtime = util_models.RuntimeOptions()

            # 阿里云 SDK 是同步的，需要在线程池中执行
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.send_sms_with_options(request, runtime),
            )

            if response.body.code == "OK":
                logger.info(
                    f"[Aliyun SMS] 发送成功: phone={phone}, template={template_code}, "
                    f"biz_id={response.body.biz_id}"
                )
                return True, None
            else:
                error_msg = f"{response.body.code}: {response.body.message}"
                logger.warning(
                    f"[Aliyun SMS] 发送失败: phone={phone}, template={template_code}, "
                    f"error={error_msg}"
                )
                return False, error_msg

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[Aliyun SMS] 发送异常: phone={phone}, template={template_code}, error={error_msg}")
            return False, error_msg

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
        # 验证码模板从配置读取
        template_code = settings.SMS_TEMPLATE_CODE
        if not template_code:
            logger.error("[Aliyun SMS] 未配置验证码模板代码")
            return False

        template_params = {"code": code}
        success, error = await self._send_sms(phone, template_code, template_params)
        return success

    async def send_notification(self, phone: str, content: str) -> bool:
        """
        发送通知短信

        Args:
            phone: 手机号
            content: 短信内容

        Returns:
            是否发送成功

        Note:
            此方法为兼容基类接口。阿里云短信必须使用模板，
            实际业务应使用 send_business_notification 方法。
        """
        logger.warning(
            "[Aliyun SMS] send_notification 不支持直接发送内容，"
            "请使用 send_business_notification 指定模板代码"
        )
        return False

    async def send_business_notification(
        self,
        phone: str,
        template_code: str,
        template_params: dict[str, str],
    ) -> tuple[bool, str | None]:
        """
        发送业务通知短信

        Args:
            phone: 手机号
            template_code: 短信模板代码（从 system_settings 读取）
            template_params: 模板参数，如 {"patient_name": "张三", "doctor": "李医生"}

        Returns:
            (是否成功, 错误信息)
        """
        return await self._send_sms(phone, template_code, template_params)
