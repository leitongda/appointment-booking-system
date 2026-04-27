"""
短信验证码服务
支持 Redis 缓存存储，可接入阿里云、腾讯云等短信服务
"""
import random
import string
from datetime import datetime
from typing import Optional
import logging

from app.core.redis import cache, RedisCache
from app.middleware.tenant_context import get_current_tenant_id
from app.db.session import get_sync_db_session
from app.models.notification_log import NotificationLog
from .factory import get_sms_provider

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
    async def send_code(cls, phone: str, code_type: str = "login", tenant_id: Optional[str] = None) -> str:
        """
        发送验证码

        Args:
            phone: 手机号
            code_type: 验证码类型（login/register/reset）
            tenant_id: 租户ID（可选，用于租户隔离。如不提供则从当前上下文获取）

        Returns:
            验证码（仅用于开发调试）

        Raises:
            ValueError: 发送过于频繁或缺少租户上下文
        """
        # 获取租户ID（用于缓存键隔离）
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if not effective_tenant_id:
            raise ValueError("缺少租户上下文，无法发送验证码")

        # 检查发送频率（带租户隔离）
        can_send, remaining = await cache.check_sms_rate_limit(
            phone, code_type, cls.SEND_INTERVAL_SECONDS, effective_tenant_id
        )
        if not can_send:
            raise ValueError(f"发送过于频繁，请{remaining}秒后重试")

        # 生成验证码
        code = cls.generate_code()

        # 存储验证码到 Redis（带租户隔离）
        await cache.set_sms_code(phone, code, code_type, cls.CODE_EXPIRE_SECONDS, tenant_id=effective_tenant_id)

        # 发送短信
        await cls._do_send(phone, code, code_type)

        return code

    @classmethod
    async def _do_send(cls, phone: str, code: str, code_type: str):
        """
        实际发送短信（委托给 provider）
        """
        tenant_id = get_current_tenant_id()
        sent_at = datetime.utcnow()

        try:
            # 委托给 provider 发送
            provider = get_sms_provider()
            success = await provider.send_verification_code(phone, code, code_type)

            if success:
                # 记录发送成功日志
                try:
                    db = get_sync_db_session()
                    try:
                        log = NotificationLog(
                            tenant_id=tenant_id,
                            channel="sms",
                            message_type=code_type,
                            title=f"{code_type}验证码",
                            content=f"验证码: {code}",
                            status="sent",
                            recipient=phone,
                            sent_at=sent_at,
                        )
                        db.add(log)
                        db.commit()
                    finally:
                        db.close()
                except Exception as e:
                    logger.error(f"创建短信通知日志失败: {e}")
            else:
                raise ValueError("短信发送失败")
        except Exception as e:
            # 记录发送失败日志
            try:
                db = get_sync_db_session()
                try:
                    log = NotificationLog(
                        tenant_id=tenant_id,
                        channel="sms",
                        message_type=code_type,
                        title=f"{code_type}验证码",
                        status="failed",
                        recipient=phone,
                        error_message=str(e),
                    )
                    db.add(log)
                    db.commit()
                finally:
                    db.close()
            except Exception as log_error:
                logger.error(f"创建短信失败日志失败: {log_error}")
            raise

    @classmethod
    async def verify_code(
        cls,
        phone: str,
        code: str,
        code_type: str = "login",
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        验证验证码（支持多租户隔离）

        Args:
            phone: 手机号
            code: 验证码
            code_type: 验证码类型
            tenant_id: 租户ID（可选，用于租户隔离验证）

        Returns:
            是否验证成功
        """
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if not effective_tenant_id:
            raise ValueError("缺少租户上下文，无法验证验证码")

        result = await cache.verify_sms_code(phone, code, code_type, effective_tenant_id)

        if result:
            logger.info(f"[SMS] 验证码验证成功: {phone}")
        else:
            logger.warning(f"[SMS] 验证码验证失败: {phone}")

        return result
