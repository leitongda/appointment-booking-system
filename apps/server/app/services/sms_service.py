"""
短信验证码服务
支持 Redis 缓存存储，可接入阿里云、腾讯云等短信服务
"""
import random
import string
from typing import Optional
import logging

from app.core.redis import cache, RedisCache

logger = logging.getLogger(__name__)


class SmsService:
    """短信验证码服务"""
    
    # 验证码有效期（秒）
    CODE_EXPIRE_SECONDS = 300  # 5 分钟
    
    # 发送间隔（秒）
    SEND_INTERVAL_SECONDS = 60
    
    @classmethod
    def generate_code(cls, length: int = 6) -> str:
        """生成随机验证码"""
        return ''.join(random.choices(string.digits, k=length))
    
    @classmethod
    async def send_code(cls, phone: str, code_type: str = "login") -> str:
        """
        发送验证码
        
        Args:
            phone: 手机号
            code_type: 验证码类型（login/register/reset）
            
        Returns:
            验证码（仅用于开发调试）
            
        Raises:
            ValueError: 发送过于频繁
        """
        # 检查发送频率
        can_send, remaining = await cache.check_sms_rate_limit(
            phone, code_type, cls.SEND_INTERVAL_SECONDS
        )
        if not can_send:
                    raise ValueError(f"发送过于频繁，请{remaining}秒后重试")
        
        # 生成验证码
        code = cls.generate_code()
        
        # 存储验证码到 Redis
        await cache.set_sms_code(phone, code, code_type, cls.CODE_EXPIRE_SECONDS)
        
        # 发送短信
        await cls._do_send(phone, code, code_type)
        
        return code
    
    @classmethod
    async def _do_send(cls, phone: str, code: str, code_type: str):
        """
        实际发送短信
        
        TODO: 接入阿里云/腾讯云短信 SDK
        """
        # 模拟发送短信（开发环境打印到控制台）
        logger.info(f"[SMS] 向 {phone} 发送{code_type}验证码: {code}")
        print(f"\n{'='*50}")
        print(f"📱 短信验证码")
        print(f"手机号: {phone}")
        print(f"验证码: {code}")
        print(f"类型: {code_type}")
        print(f"有效期: {cls.CODE_EXPIRE_SECONDS // 60}分钟")
        print(f"{'='*50}\n")
        
        # 生产环境接入短信服务商示例：
        # if settings.SMS_PROVIDER == 'aliyun':
        #     await cls._send_aliyun(phone, code, code_type)
        # elif settings.SMS_PROVIDER == 'tencent':
        #     await cls._send_tencent(phone, code, code_type)
    
    @classmethod
    async def verify_code(cls, phone: str, code: str, code_type: str = "login") -> bool:
        """
        验证验证码
        
        Args:
            phone: 手机号
            code: 验证码
            code_type: 验证码类型
            
        Returns:
            是否验证成功
        """
        result = await cache.verify_sms_code(phone, code, code_type)
        
        if result:
            logger.info(f"[SMS] 验证码验证成功: {phone}")
        else:
            logger.warning(f"[SMS] 验证码验证失败: {phone}")
        
        return result
    
    # ==================== 阿里云短信 ====================
    
    @classmethod
    async def _send_aliyun(cls, phone: str, code: str, code_type: str):
        """
        阿里云短信发送
        
        需要安装: pip install alibabacloud_dysmsapi20170525
        """
        # from alibabacloud_dysmsapi20170525.client import Client
        # from alibabacloud_dysmsapi20170525 import models as sms_models
        # from alibabacloud_tea_openapi import models as open_api_models
        # 
        # config = open_api_models.Config(
        #     access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
        #     access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET
        # )
        # config.endpoint = 'dysmsapi.aliyuncs.com'
        # 
        # client = Client(config)
        # 
        # request = sms_models.SendSmsRequest(
        #     phone_numbers=phone,
        #     sign_name=settings.SMS_SIGN_NAME,
        #     template_code=settings.SMS_TEMPLATE_CODE,
        #     template_param=f'{{"code":"{code}"}}'
        # )
        # 
        # response = client.send_sms(request)
        # if response.body.code != 'OK':
        #     raise ValueError(f"短信发送失败: {response.body.message}")
        pass
    
    # ==================== 腾讯云短信 ====================
    
    @classmethod
    async def _send_tencent(cls, phone: str, code: str, code_type: str):
        """
        腾讯云短信发送
        
        需要安装: pip install tencentcloud-sdk-python
        """
        # from tencentcloud.common import credential
        # from tencentcloud.sms.v20210111 import sms_client, models
        # 
        # cred = credential.Credential(
        #     settings.TENCENT_SECRET_ID,
        #     settings.TENCENT_SECRET_KEY
        # )
        # 
        # client = sms_client.SmsClient(cred, "ap-guangzhou")
        # 
        # req = models.SendSmsRequest()
        # req.SmsSdkAppId = settings.SMS_SDK_APP_ID
        # req.SignName = settings.SMS_SIGN_NAME
        # req.TemplateId = settings.SMS_TEMPLATE_ID
        # req.PhoneNumberSet = [f"+86{phone}"]
        # req.TemplateParamSet = [code]
        # 
        # resp = client.SendSms(req)
        # if resp.SendStatusSet[0].Code != "Ok":
        #     raise ValueError(f"短信发送失败: {resp.SendStatusSet[0].Message}")
        pass
