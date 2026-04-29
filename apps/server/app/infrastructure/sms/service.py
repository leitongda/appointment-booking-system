"""
短信服务
支持 Redis 缓存存储，可接入阿里云、腾讯云等短信服务
包含验证码发送和业务通知功能
"""
import random
import string
from datetime import datetime
from typing import Any, Dict, Optional
import logging

from sqlalchemy import select, text

from app.core.redis import cache, RedisCache
from app.middleware.tenant_context import get_current_tenant_id
from app.db.session import get_sync_db_session
from app.models.notification_log import NotificationLog
from app.models.settings import SystemSetting
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

    # ==================== 业务通知方法 ====================

    @classmethod
    async def _get_template_code(
        cls,
        template_key: str,
        tenant_id: str,
    ) -> Optional[str]:
        """
        从 system_settings 读取短信模板代码

        Args:
            template_key: 模板配置键名（如 appointment_success_template）
            tenant_id: 租户ID

        Returns:
            模板代码，不存在则返回 None
        """
        try:
            db = get_sync_db_session()
            try:
                result = db.execute(
                    select(SystemSetting).where(
                        text(
                            "category = 'sms' AND key = :key AND (store_id IS NULL OR store_id = '')"
                        )
                    ).params(key=template_key)
                )
                setting = result.scalar_one_or_none()
                return setting.value if setting else None
            finally:
                db.close()
        except Exception as e:
            logger.error(f"读取短信模板配置失败: key={template_key}, error={e}")
            return None

    @classmethod
    async def _send_business_sms(
        cls,
        tenant_id: str,
        phone: str,
        template_code: str,
        template_params: Dict[str, Any],
        message_type: str,
        title: str,
        content: str,
        user_id: Optional[str] = None,
        store_id: Optional[str] = None,
        related_id: Optional[str] = None,
    ) -> bool:
        """
        发送业务短信（内部方法）

        Args:
            tenant_id: 租户ID
            phone: 手机号
            template_code: 短信模板代码
            template_params: 模板参数
            message_type: 消息类型（用于日志）
            title: 消息标题（用于日志）
            content: 消息内容（用于日志）
            user_id: 用户ID（用于日志）
            store_id: 门店ID（用于日志）
            related_id: 关联业务ID（用于日志）

        Returns:
            是否发送成功
        """
        sent_at = datetime.utcnow()
        success = False
        error_msg = None

        try:
            provider = get_sms_provider()

            # 检查 provider 是否支持业务通知
            if hasattr(provider, "send_business_notification"):
                success, error_msg = await provider.send_business_notification(
                    phone=phone,
                    template_code=template_code,
                    template_params=template_params,
                )
            else:
                # 降级到 send_notification（仅适用于 mock provider）
                logger.warning(
                    f"[SMS] Provider 不支持 send_business_notification，"
                    f"降级使用 send_notification: {template_code}"
                )
                # 将模板参数格式化为可读内容
                content_str = "; ".join(f"{k}={v}" for k, v in template_params.items())
                success = await provider.send_notification(phone, content_str)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[SMS] 业务短信发送异常: {e}")

        # 记录 NotificationLog
        try:
            db = get_sync_db_session()
            try:
                log = NotificationLog(
                    tenant_id=tenant_id,
                    store_id=store_id,
                    user_id=user_id,
                    user_type="patient",
                    channel="sms",
                    message_type=message_type,
                    title=title,
                    content=content,
                    status="sent" if success else "failed",
                    recipient=phone,
                    related_id=related_id,
                    sent_at=sent_at if success else None,
                    error_message=error_msg,
                )
                db.add(log)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"创建短信通知日志失败: {e}")

        return success

    @classmethod
    async def send_appointment_success(
        cls,
        tenant_id: str,
        phone: str,
        variables: Dict[str, Any],
        user_id: Optional[str] = None,
        store_id: Optional[str] = None,
        appointment_id: Optional[str] = None,
    ) -> bool:
        """
        发送预约成功通知短信

        Args:
            tenant_id: 租户ID
            phone: 手机号
            variables: 模板变量，如 {"patient_name": "张三", "doctor": "李医生", "time": "2024-01-01 09:00"}
            user_id: 用户ID
            store_id: 门店ID
            appointment_id: 预约ID

        Returns:
            是否发送成功
        """
        template_code = await cls._get_template_code("appointment_success_template", tenant_id)
        if not template_code:
            logger.warning(f"[SMS] 未配置预约成功短信模板，跳过发送")
            return False

        # 构建模板参数（阿里云要求参数值为字符串）
        template_params = {k: str(v) for k, v in variables.items()}

        # 构建日志内容
        content = f"预约成功: {variables.get('patient_name', '')} - {variables.get('doctor', '')} - {variables.get('time', '')}"

        return await cls._send_business_sms(
            tenant_id=tenant_id,
            phone=phone,
            template_code=template_code,
            template_params=template_params,
            message_type="appointment_success",
            title="预约成功",
            content=content,
            user_id=user_id,
            store_id=store_id,
            related_id=appointment_id,
        )

    @classmethod
    async def send_appointment_reminder(
        cls,
        tenant_id: str,
        phone: str,
        variables: Dict[str, Any],
        user_id: Optional[str] = None,
        store_id: Optional[str] = None,
        appointment_id: Optional[str] = None,
    ) -> bool:
        """
        发送就诊提醒通知短信

        Args:
            tenant_id: 租户ID
            phone: 手机号
            variables: 模板变量，如 {"patient_name": "张三", "doctor": "李医生", "time": "2024-01-01 09:00"}
            user_id: 用户ID
            store_id: 门店ID
            appointment_id: 预约ID

        Returns:
            是否发送成功
        """
        template_code = await cls._get_template_code("appointment_reminder_template", tenant_id)
        if not template_code:
            logger.warning(f"[SMS] 未配置就诊提醒短信模板，跳过发送")
            return False

        template_params = {k: str(v) for k, v in variables.items()}
        content = f"就诊提醒: {variables.get('patient_name', '')} - {variables.get('doctor', '')} - {variables.get('time', '')}"

        return await cls._send_business_sms(
            tenant_id=tenant_id,
            phone=phone,
            template_code=template_code,
            template_params=template_params,
            message_type="appointment_reminder",
            title="就诊提醒",
            content=content,
            user_id=user_id,
            store_id=store_id,
            related_id=appointment_id,
        )

    @classmethod
    async def send_appointment_cancelled(
        cls,
        tenant_id: str,
        phone: str,
        variables: Dict[str, Any],
        user_id: Optional[str] = None,
        store_id: Optional[str] = None,
        appointment_id: Optional[str] = None,
    ) -> bool:
        """
        发送取消预约通知短信

        Args:
            tenant_id: 租户ID
            phone: 手机号
            variables: 模板变量，如 {"patient_name": "张三", "doctor": "李医生", "time": "2024-01-01 09:00", "reason": "个人原因"}
            user_id: 用户ID
            store_id: 门店ID
            appointment_id: 预约ID

        Returns:
            是否发送成功
        """
        template_code = await cls._get_template_code("appointment_cancelled_template", tenant_id)
        if not template_code:
            logger.warning(f"[SMS] 未配置取消预约短信模板，跳过发送")
            return False

        template_params = {k: str(v) for k, v in variables.items()}
        content = f"预约已取消: {variables.get('patient_name', '')} - {variables.get('doctor', '')} - {variables.get('time', '')}"

        return await cls._send_business_sms(
            tenant_id=tenant_id,
            phone=phone,
            template_code=template_code,
            template_params=template_params,
            message_type="appointment_cancelled",
            title="预约已取消",
            content=content,
            user_id=user_id,
            store_id=store_id,
            related_id=appointment_id,
        )

    @classmethod
    async def send_stop_clinic_notice(
        cls,
        tenant_id: str,
        phone: str,
        variables: Dict[str, Any],
        user_id: Optional[str] = None,
        store_id: Optional[str] = None,
        appointment_id: Optional[str] = None,
    ) -> bool:
        """
        发送停诊通知短信

        Args:
            tenant_id: 租户ID
            phone: 手机号
            variables: 模板变量，如 {"patient_name": "张三", "doctor": "李医生", "date": "2024-01-01", "reason": "医生临时有事"}
            user_id: 用户ID
            store_id: 门店ID
            appointment_id: 预约ID

        Returns:
            是否发送成功
        """
        template_code = await cls._get_template_code("stop_clinic_template", tenant_id)
        if not template_code:
            logger.warning(f"[SMS] 未配置停诊短信模板，跳过发送")
            return False

        template_params = {k: str(v) for k, v in variables.items()}
        content = f"停诊通知: {variables.get('patient_name', '')} - {variables.get('doctor', '')} - {variables.get('date', '')}"

        return await cls._send_business_sms(
            tenant_id=tenant_id,
            phone=phone,
            template_code=template_code,
            template_params=template_params,
            message_type="stop_clinic",
            title="停诊通知",
            content=content,
            user_id=user_id,
            store_id=store_id,
            related_id=appointment_id,
        )
