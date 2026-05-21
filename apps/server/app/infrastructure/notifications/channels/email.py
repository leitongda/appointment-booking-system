"""邮件渠道适配器"""
import logging
from datetime import datetime

from sqlalchemy import select

from app.schemas.notification import NotificationEvent, NotificationContent
from app.models.notification_log import NotificationLog
from app.models.account import Account
from app.models.user import User
from app.infrastructure.notifications.channels.base import BaseNotificationChannel
from app.infrastructure.email.service import EmailService


logger = logging.getLogger(__name__)


class EmailChannel(BaseNotificationChannel):
    """邮件渠道

    通过 EmailService 发送邮件通知。
    """

    @property
    def channel_name(self) -> str:
        return "email"

    async def validate_recipient(self, event: NotificationEvent) -> tuple[bool, str | None]:
        """邮件需要邮箱地址，支持从数据库 fallback 查询"""
        if not event.recipient_email:
            # 尝试从数据库获取邮箱
            if event.recipient_type == "patient":
                result = await self.db.execute(
                    select(User.email).where(User.id == event.recipient_id)
                )
                email = await result.scalar_one_or_none()
                if not email:
                    return False, "用户未设置邮箱或缺少邮箱地址"
                event.recipient_email = email
            else:
                # 优先查 Account 表
                result = await self.db.execute(
                    select(Account.email).where(Account.id == event.recipient_id)
                )
                email = await result.scalar_one_or_none()
                if not email:
                    return False, "缺少接收人邮箱"
                event.recipient_email = email
        return True, None

    async def send(self, event: NotificationEvent, content: NotificationContent) -> bool:
        """发送邮件"""
        try:
            # 检查用户是否启用了邮件通知偏好
            from app.common.notification_preference import check_notification_preference
            pref_ok = await check_notification_preference(
                self.db, event.recipient_id, event.recipient_type, "email", event.message_type
            )
            if not pref_ok:
                logger.info(f"[邮件] 用户已禁用邮件通知: user={event.recipient_id}, type={event.message_type}")
                return False

            email_service = EmailService(self.db)

            # 尝试使用模板发送
            success = await email_service.send_by_template(
                template_code=event.template_code,
                to_email=event.recipient_email,
                variables=event.variables,
            )

            dispatch_meta = (event.extra_data or {}).get("_dispatch", {})
            if success:
                # 记录通知日志
                log = NotificationLog(
                    tenant_id=event.tenant_id,
                    store_id=event.store_id,
                    user_id=event.recipient_id,
                    user_type=event.recipient_type,
                    channel=self.channel_name,
                    message_type=event.message_type,
                    title=content.title,
                    content=content.content,
                    status="sent",
                    recipient=event.recipient_email,
                    related_id=event.related_id,
                    sent_at=datetime.utcnow(),
                    primary_channel=dispatch_meta.get("primary_channel"),
                    fallback_reason=dispatch_meta.get("fallback_reason"),
                    channel_attempt_order=dispatch_meta.get("channel_attempt_order"),
                )
                self.db.add(log)

                logger.info(f"[邮件] 发送成功: user={event.recipient_id}, email={event.recipient_email}")
            else:
                # 记录失败日志
                log = NotificationLog(
                    tenant_id=event.tenant_id,
                    store_id=event.store_id,
                    user_id=event.recipient_id,
                    user_type=event.recipient_type,
                    channel=self.channel_name,
                    message_type=event.message_type,
                    title=content.title,
                    status="failed",
                    recipient=event.recipient_email,
                    related_id=event.related_id,
                    error_message="邮件发送失败",
                    primary_channel=dispatch_meta.get("primary_channel"),
                    fallback_reason=dispatch_meta.get("fallback_reason"),
                    channel_attempt_order=dispatch_meta.get("channel_attempt_order"),
                )
                self.db.add(log)

            return success

        except Exception as e:
            logger.error(f"[邮件] 发送失败: {e}", exc_info=True)

            # 记录失败日志
            try:
                log = NotificationLog(
                    tenant_id=event.tenant_id,
                    store_id=event.store_id,
                    user_id=event.recipient_id,
                    user_type=event.recipient_type,
                    channel=self.channel_name,
                    message_type=event.message_type,
                    title=content.title,
                    status="failed",
                    recipient=event.recipient_email or "",
                    related_id=event.related_id,
                    error_message=str(e),
                )
                self.db.add(log)
            except Exception:
                pass

            return False
