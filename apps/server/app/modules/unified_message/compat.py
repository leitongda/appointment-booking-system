"""兼容层：让业务模块无感知地使用统一消息服务

所有租户已迁移至统一消息系统，不再检查 feature flag。
此模块保留供已有调用者（MessageServiceCompat）使用，方法签名不变。
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.unified_message.schemas import NotificationEvent
from app.modules.unified_message.service import UnifiedMessageService

logger = logging.getLogger(__name__)


class MessageServiceCompat:
    """兼容层：委托 UnifiedMessageService 处理所有消息发送和查询

    使用方式与旧 MessageService 一致：MessageServiceCompat(db)
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._new_service: UnifiedMessageService | None = None

    @property
    def new_service(self) -> UnifiedMessageService:
        if self._new_service is None:
            self._new_service = UnifiedMessageService(self.db)
        return self._new_service

    async def send_appointment_notification(
        self,
        user_id: str,
        user_type: str,
        title: str,
        content: str,
        appointment_id: str,
        template_code: str | None = None,
        template_variables: dict | None = None,
    ):
        """发送预约通知"""
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        message_type_map = {
            "预约成功": "appointment_success",
            "就诊提醒": "appointment_reminder",
            "叫号通知": "queue_call",
            "预约已取消": "appointment_cancelled",
        }
        message_type = message_type_map.get(title, "appointment")

        # 获取接收人联系方式
        from app.modules.messages.service_messages import _get_user_contact_info
        contact = await _get_user_contact_info(self.db, user_id)

        event = NotificationEvent(
            tenant_id=tenant_id,
            recipient_id=user_id,
            recipient_type=user_type,
            recipient_phone=contact.phone,
            recipient_openid=contact.openid,
            recipient_email=contact.email,
            template_code=template_code or message_type,
            variables=template_variables or {},
            message_type=message_type,
            related_id=appointment_id,
            title=title,
            content=content,
        )
        result = await self.new_service.send(event)
        # 返回兼容格式（旧方法返回 Message 或 None）
        if result.success and result.group_id:
            from sqlalchemy import select

            from app.modules.unified_message.models import NotificationRecipient
            recipient = await self.db.execute(
                select(NotificationRecipient).where(
                    NotificationRecipient.group_id == result.group_id
                ).limit(1)
            )
            return recipient.scalar_one_or_none()
        return None

    async def send_schedule_notification(
        self,
        doctor_id: str,
        title: str,
        content: str,
        schedule_id: str | None = None,
        template_code: str | None = None,
        template_variables: dict | None = None,
    ):
        """发送排班通知"""
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        event = NotificationEvent(
            tenant_id=tenant_id,
            recipient_id=doctor_id,
            recipient_type="doctor",
            template_code=template_code or "schedule",
            variables=template_variables or {},
            message_type="schedule",
            related_id=schedule_id,
            title=title,
            content=content,
        )
        result = await self.new_service.send(event)
        if result.success and result.group_id:
            from sqlalchemy import select

            from app.modules.unified_message.models import NotificationRecipient
            recipient = await self.db.execute(
                select(NotificationRecipient).where(
                    NotificationRecipient.group_id == result.group_id
                ).limit(1)
            )
            return recipient.scalar_one_or_none()
        return None

    async def send_stop_clinic_notification(
        self,
        user_id: str,
        user_type: str,
        title: str,
        content: str,
        appointment_id: str | None = None,
        template_code: str | None = None,
        template_variables: dict | None = None,
    ):
        """发送停诊通知"""
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        # 获取接收人联系方式
        from app.modules.messages.service_messages import _get_user_contact_info
        contact = await _get_user_contact_info(self.db, user_id)

        event = NotificationEvent(
            tenant_id=tenant_id,
            recipient_id=user_id,
            recipient_type=user_type,
            recipient_phone=contact.phone,
            recipient_openid=contact.openid,
            recipient_email=contact.email,
            template_code=template_code or "stop_clinic_patient",
            variables=template_variables or {},
            message_type="stop_clinic",
            related_id=appointment_id,
            title=title,
            content=content,
        )
        result = await self.new_service.send(event)
        if result.success and result.group_id:
            from sqlalchemy import select

            from app.modules.unified_message.models import NotificationRecipient
            recipient = await self.db.execute(
                select(NotificationRecipient).where(
                    NotificationRecipient.group_id == result.group_id
                ).limit(1)
            )
            return recipient.scalar_one_or_none()
        return None

    async def send_system_notification(
        self,
        user_id: str,
        user_type: str,
        title: str,
        content: str,
    ):
        """发送系统通知"""
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        event = NotificationEvent(
            tenant_id=tenant_id,
            recipient_id=user_id,
            recipient_type=user_type,
            template_code="system",
            variables={},
            message_type="system",
            title=title,
            content=content,
        )
        result = await self.new_service.send(event)
        if result.success and result.group_id:
            from sqlalchemy import select

            from app.modules.unified_message.models import NotificationRecipient
            recipient = await self.db.execute(
                select(NotificationRecipient).where(
                    NotificationRecipient.group_id == result.group_id
                ).limit(1)
            )
            return recipient.scalar_one_or_none()
        return None

    # 查询方法：直接委托 UnifiedMessageService
    async def get_user_messages(self, user_id, user_type, query):
        return await self.new_service.get_user_messages(user_id, user_type, query)

    async def get_unread_count(self, user_id, user_type):
        return await self.new_service.get_unread_count(user_id, user_type)

    async def mark_as_read(self, message_id, user_id):
        return await self.new_service.mark_as_read(message_id, user_id)

    async def mark_all_as_read(self, user_id, user_type, message_type=None):
        return await self.new_service.mark_all_as_read(user_id, user_type, message_type)

    async def delete(self, message_id, user_id):
        return await self.new_service.delete(message_id, user_id)

    async def delete_all_read(self, user_id, user_type):
        return await self.new_service.delete_all_read(user_id, user_type)
