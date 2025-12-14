"""
短信验证码服务
目前为模拟实现，后续可接入阿里云、腾讯云等短信服务
"""
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class SmsService:
    """短信验证码服务"""
    
    # 内存存储验证码（生产环境应使用 Redis）
    _codes: Dict[str, dict] = {}
    
    # 验证码有效期（分钟）
    CODE_EXPIRE_MINUTES = 5
    
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
        key = f"{phone}:{code_type}"
        
        # 检查发送频率
        if key in cls._codes:
            last_send = cls._codes[key].get("send_time")
            if last_send:
                elapsed = (datetime.now() - last_send).total_seconds()
                if elapsed < cls.SEND_INTERVAL_SECONDS:
                    remaining = int(cls.SEND_INTERVAL_SECONDS - elapsed)
                    raise ValueError(f"发送过于频繁，请{remaining}秒后重试")
        
        # 生成验证码
        code = cls.generate_code()
        
        # 存储验证码
        cls._codes[key] = {
            "code": code,
            "send_time": datetime.now(),
            "expire_time": datetime.now() + timedelta(minutes=cls.CODE_EXPIRE_MINUTES),
            "verified": False
        }
        
        # 模拟发送短信（实际项目中应调用短信服务商API）
        logger.info(f"[SMS] 向 {phone} 发送{code_type}验证码: {code}")
        print(f"\n{'='*50}")
        print(f"📱 短信验证码 (模拟发送)")
        print(f"手机号: {phone}")
        print(f"验证码: {code}")
        print(f"类型: {code_type}")
        print(f"有效期: {cls.CODE_EXPIRE_MINUTES}分钟")
        print(f"{'='*50}\n")
        
        return code
    
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
        key = f"{phone}:{code_type}"
        
        if key not in cls._codes:
            logger.warning(f"[SMS] 验证码不存在: {phone}")
            return False
        
        stored = cls._codes[key]
        
        # 检查是否已过期
        if datetime.now() > stored["expire_time"]:
            logger.warning(f"[SMS] 验证码已过期: {phone}")
            del cls._codes[key]
            return False
        
        # 检查是否已使用
        if stored["verified"]:
            logger.warning(f"[SMS] 验证码已使用: {phone}")
            return False
        
        # 验证码匹配
        if stored["code"] == code:
            stored["verified"] = True
            logger.info(f"[SMS] 验证码验证成功: {phone}")
            return True
        
        logger.warning(f"[SMS] 验证码错误: {phone}, 输入: {code}, 正确: {stored['code']}")
        return False
    
    @classmethod
    def clear_expired(cls):
        """清理过期的验证码"""
        now = datetime.now()
        expired_keys = [
            key for key, data in cls._codes.items()
            if now > data["expire_time"]
        ]
        for key in expired_keys:
            del cls._codes[key]
        
        if expired_keys:
            logger.info(f"[SMS] 清理了 {len(expired_keys)} 个过期验证码")
