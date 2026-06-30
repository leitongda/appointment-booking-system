"""腾讯云短信服务提供商"""
import asyncio
import logging
from collections.abc import Mapping, Sequence
from typing import Any

from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.sms.v20210111 import sms_client, models as sms_models

from app.core.config import settings

from ..provider_base import SmsProvider

logger = logging.getLogger(__name__)


class TencentSmsProvider(SmsProvider):
    """腾讯云短信服务提供商

    文档：https://cloud.tencent.com/document/product/382/55981

    配置项：
        TENCENT_SECRET_ID: 腾讯云 SecretId
        TENCENT_SECRET_KEY: 腾讯云 SecretKey
        TENCENT_SMS_APP_ID: 短信应用 ID
        TENCENT_SMS_SIGN_NAME: 短信签名
        TENCENT_SMS_REGION: 腾讯云短信地域，默认 ap-guangzhou
    """

    def __init__(self):
        self._client: sms_client.SmsClient | None = None
        self._app_id: str | None = None
        self._sign_name: str | None = None

    @property
    def client(self) -> sms_client.SmsClient:
        """懒加载腾讯云 SMS 客户端"""
        if self._client is None:
            if not settings.TENCENT_SECRET_ID or not settings.TENCENT_SECRET_KEY:
                raise ValueError("腾讯云短信配置缺失：TENCENT_SECRET_ID 或 TENCENT_SECRET_KEY 未设置")
            cred = credential.Credential(
                settings.TENCENT_SECRET_ID,
                settings.TENCENT_SECRET_KEY,
            )
            self._client = sms_client.SmsClient(cred, settings.TENCENT_SMS_REGION)
        return self._client

    @property
    def app_id(self) -> str:
        """获取短信应用 ID"""
        if self._app_id is None:
            self._app_id = settings.TENCENT_SMS_APP_ID or ""
            if not self._app_id:
                logger.warning("[Tencent SMS] TENCENT_SMS_APP_ID 未配置")
        return self._app_id

    @property
    def sign_name(self) -> str:
        """获取短信签名"""
        if self._sign_name is None:
            self._sign_name = settings.TENCENT_SMS_SIGN_NAME or settings.SMS_SIGN_NAME or ""
        return self._sign_name

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """腾讯云短信要求手机号使用 E.164 格式，国内 11 位手机号自动补 +86。"""
        normalized = phone.strip()
        if normalized.startswith("+"):
            return normalized
        if normalized.isdigit() and len(normalized) == 11 and normalized.startswith("1"):
            return f"+86{normalized}"
        return normalized

    @staticmethod
    def _normalize_template_params(
        template_params: Mapping[str, Any] | Sequence[Any] | None,
    ) -> list[str]:
        """将业务层 dict/list 模板参数统一转换为腾讯云需要的位置参数列表。"""
        if not template_params:
            return []
        if isinstance(template_params, Mapping):
            return [str(value) for value in template_params.values()]
        if isinstance(template_params, (str, bytes)):
            return [template_params.decode() if isinstance(template_params, bytes) else template_params]
        return [str(value) for value in template_params]

    async def _send_sms(
        self,
        phone: str,
        template_id: str,
        template_params: list[str],
    ) -> tuple[bool, str | None]:
        """
        发送短信（内部方法）

        Args:
            phone: 手机号（支持国际格式，如 +8613800138000）
            template_id: 模板 ID
            template_params: 模板参数列表

        Returns:
            (是否成功, 错误信息)
        """
        try:
            if not self.app_id:
                return False, "TENCENT_SMS_APP_ID 未配置"
            if not self.sign_name:
                return False, "TENCENT_SMS_SIGN_NAME 或 SMS_SIGN_NAME 未配置"

            # 构建请求
            req = sms_models.SendSmsRequest()
            req.PhoneNumberSet = [self._normalize_phone(phone)]
            req.SmsSdkAppId = self.app_id
            req.SignName = self.sign_name
            req.TemplateId = template_id
            req.TemplateParamSet = template_params

            # 腾讯云 SDK 是同步的，需要在线程池中执行
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.SendSms(req),
            )

            # 检查响应
            if response.SendStatusSet and len(response.SendStatusSet) > 0:
                status = response.SendStatusSet[0]
                if status.Code == "Ok":
                    logger.info(
                        f"[Tencent SMS] 发送成功: phone={phone}, template={template_id}, "
                        f"serial_no={status.SerialNo}"
                    )
                    return True, None
                else:
                    error_msg = f"{status.Code}: {status.Message}"
                    logger.warning(
                        f"[Tencent SMS] 发送失败: phone={phone}, template={template_id}, "
                        f"error={error_msg}"
                    )
                    return False, error_msg
            else:
                error_msg = "响应中无发送状态"
                logger.warning(f"[Tencent SMS] 发送异常: phone={phone}, template={template_id}, error={error_msg}")
                return False, error_msg

        except TencentCloudSDKException as e:
            error_msg = f"SDK 错误: {e.code} - {e.message}"
            logger.error(f"[Tencent SMS] 发送异常: phone={phone}, template={template_id}, error={error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[Tencent SMS] 发送异常: phone={phone}, template={template_id}, error={error_msg}")
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
        template_id = settings.SMS_TEMPLATE_CODE
        if not template_id:
            logger.error("[Tencent SMS] 未配置验证码模板 ID (SMS_TEMPLATE_CODE)")
            return False

        template_params = [code]
        success, error = await self._send_sms(phone, template_id, template_params)
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
            此方法为兼容基类接口。腾讯云短信必须使用模板，
            实际业务应使用 send_business_notification 方法。
        """
        logger.warning(
            "[Tencent SMS] send_notification 不支持直接发送内容，"
            "请使用 send_business_notification 指定模板 ID"
        )
        return False

    async def send_business_notification(
        self,
        phone: str,
        template_id: str,
        template_params: list[str],
    ) -> tuple[bool, str | None]:
        """
        发送业务通知短信

        Args:
            phone: 手机号
            template_id: 短信模板 ID（从 system_settings 读取）
            template_params: 模板参数，支持 dict 或列表，如 {"patient_name": "张三"} / ["张三", "李医生"]

        Returns:
            (是否成功, 错误信息)
        """
        return await self._send_sms(phone, template_id, self._normalize_template_params(template_params))
