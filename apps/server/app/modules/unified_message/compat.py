"""兼容层：让业务模块无感知地切换到新服务

通过 FeatureFlagService.is_beta_enabled() 运行时检查，
逐租户灰度切换，无需重启服务。
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.feature_flags import FeatureFlagService
from app.modules.unified_message.service import UnifiedMessageService
from app.modules.unified_message.schemas import NotificationEvent

logger = logging.getLogger(__name__)


class MessageServiceCompat:
    """兼容层：包装旧 MessageService 的 3 个活跃 send_* 方法

    beta_unified_message=False → 转发到旧 MessageService
    beta_unified_message=True  → 转发到新 UnifiedMessageService

    使用方式与 MessageService 一致：MessageServiceCompat(db)
    """

    def __init__(self, db: AsyncSession):
        from app.modules.messages.service_messages import MessageService
        self.db = db
        self.old_service = MessageService(db)
        self._new_service: Optional[UnifiedMessageService] = None

    @property
    def new_service(self) -> UnifiedMessageService:
        if self._new_service is None:
            self._new_service = UnifiedMessageService(self.db)
        return self._new_service

    async def _should_use_new(self, tenant_id: str) -> bool:
        """运行时检查 feature flag，支持动态切换"""
        try:
            return await FeatureFlagService.is_beta_enabled(
                self.db, tenant_id, "beta_unified_message"
            )
        except Exception:
            return False

    async def send_appointment_notification(
        self,
        user_id: str,
        user_type: str,
        title: str,
        content: str,
        appointment_id: str,
        template_code: Optional[str] = None,
        template_variables: Optional[dict] = None,
    ):
        """发送预约通知"""
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        if tenant_id and await self._should_use_new(tenant_id):
            # 确定消息类型
            message_type_map = {
                "预约成功": "appointment_success",
                "就诊提醒": "appointment_reminder",
                "叫号通知": "queue_call",
                "预约已取消": "appointment_cancelled",
            }
            message_type = message_type_map.get(title, "appointment")

            # 获取接收人联系方式
            from app.modules.messages.service_messages import _get_user_contact_info
            phone, openid = await _get_user_contact_info(self.db, user_id)

            event = NotificationEvent(
                tenant_id=tenant_id,
                recipient_id=user_id,
                recipient_type=user_type,
                recipient_phone=phone,
                recipient_openid=openid,
                template_code=template_code or message_type,
                variables=template_variables or {},
                message_type=message_type,
                related_id=appointment_id,
                title=title,
                content=content,
            )
            try:
                result = await self.new_service.send(event)
                # 返回兼容格式（旧方法返回 Message 或 None）
                if result.success and result.group_id:
                    from app.modules.unified_message.models import NotificationRecipient
                    from sqlalchemy import select
                    recipient = await self.db.execute(
                        select(NotificationRecipient).where(
                            NotificationRecipient.group_id == result.group_id
                        ).limit(1)
                    )
                    return recipient.scalar_one_or_none()
            except Exception as e:
                logger.error(f"[兼容层] 新服务发送失败，降级到旧服务: {e}", exc_info=True)
            # 新服务失败时降级到旧服务
            return await self.old_service.send_appointment_notification(
                user_id=user_id,
                user_type=user_type,
                title=title,
                content=content,
                appointment_id=appointment_id,
                template_code=template_code,
                template_variables=template_variables,
            )
        else:
            return await self.old_service.send_appointment_notification(
                user_id=user_id,
                user_type=user_type,
                title=title,
                content=content,
                appointment_id=appointment_id,
                template_code=template_code,
                template_variables=template_variables,
            )

    async def send_schedule_notification(
        self,
        doctor_id: str,
        title: str,
        content: str,
        schedule_id: Optional[str] = None,
        template_code: Optional[str] = None,
        template_variables: Optional[dict] = None,
    ):
        """发送排班通知"""
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        if tenant_id and await self._should_use_new(tenant_id):
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
            try:
                result = await self.new_service.send(event)
                if result.success and result.group_id:
                    from app.modules.unified_message.models import NotificationRecipient
                    from sqlalchemy import select
                    recipient = await self.db.execute(
                        select(NotificationRecipient).where(
                            NotificationRecipient.group_id == result.group_id
                        ).limit(1)
                    )
                    return recipient.scalar_one_or_none()
            except Exception as e:
                logger.error(f"[兼容层] 新服务发送失败，降级到旧服务: {e}", exc_info=True)
            # 新服务失败时降级到旧服务
            return await self.old_service.send_schedule_notification(
                doctor_id=doctor_id,
                title=title,
                content=content,
                schedule_id=schedule_id,
                template_code=template_code,
                template_variables=template_variables,
            )
        else:
            return await self.old_service.send_schedule_notification(
                doctor_id=doctor_id,
                title=title,
                content=content,
                schedule_id=schedule_id,
                template_code=template_code,
                template_variables=template_variables,
            )

    async def send_stop_clinic_notification(
        self,
        user_id: str,
        user_type: str,
        title: str,
        content: str,
        appointment_id: Optional[str] = None,
        template_code: Optional[str] = None,
        template_variables: Optional[dict] = None,
    ):
        """发送停诊通知"""
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        if tenant_id and await self._should_use_new(tenant_id):
            # 获取接收人联系方式
            from app.modules.messages.service_messages import _get_user_contact_info
            phone, openid = await _get_user_contact_info(self.db, user_id)

            event = NotificationEvent(
                tenant_id=tenant_id,
                recipient_id=user_id,
                recipient_type=user_type,
                recipient_phone=phone,
                recipient_openid=openid,
                template_code=template_code or "stop_clinic_patient",
                variables=template_variables or {},
                message_type="stop_clinic",
                related_id=appointment_id,
                title=title,
                content=content,
            )
            try:
                result = await self.new_service.send(event)
                if result.success and result.group_id:
                    from app.modules.unified_message.models import NotificationRecipient
                    from sqlalchemy import select
                    recipient = await self.db.execute(
                        select(NotificationRecipient).where(
                            NotificationRecipient.group_id == result.group_id
                        ).limit(1)
                    )
                    return recipient.scalar_one_or_none()
            except Exception as e:
                logger.error(f"[兼容层] 新服务发送失败，降级到旧服务: {e}", exc_info=True)
            # 新服务失败时降级到旧服务
            return await self.old_service.send_stop_clinic_notification(
                user_id=user_id,
                user_type=user_type,
                title=title,
                content=content,
                appointment_id=appointment_id,
                template_code=template_code,
                template_variables=template_variables,
            )
        else:
            return await self.old_service.send_stop_clinic_notification(
                user_id=user_id,
                user_type=user_type,
                title=title,
                content=content,
                appointment_id=appointment_id,
                template_code=template_code,
                template_variables=template_variables,
            )

    async def send_system_notification(
        self,
        user_id: str,
        user_type: str,
        title: str,
        content: str,
    ):
        """发送系统通知（最小实现，无外部调用者，仅保留接口完整性）"""
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        if tenant_id and await self._should_use_new(tenant_id):
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
            try:
                result = await self.new_service.send(event)
                if result.success and result.group_id:
                    from app.modules.unified_message.models import NotificationRecipient
                    from sqlalchemy import select
                    recipient = await self.db.execute(
                        select(NotificationRecipient).where(
                            NotificationRecipient.group_id == result.group_id
                        ).limit(1)
                    )
                    return recipient.scalar_one_or_none()
            except Exception as e:
                logger.error(f"[兼容层] 新服务发送失败，降级到旧服务: {e}", exc_info=True)
            # 新服务失败时降级到旧服务
            return await self.old_service.send_system_notification(
                user_id=user_id,
                user_type=user_type,
                title=title,
                content=content,
            )
        else:
            return await self.old_service.send_system_notification(
                user_id=user_id,
                user_type=user_type,
                title=title,
                content=content,
            )

    # 查询方法：根据 feature flag 切换
    async def get_user_messages(self, user_id, user_type, query):
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        if tenant_id and await self._should_use_new(tenant_id):
            try:
                return await self.new_service.get_user_messages(user_id, user_type, query)
            except Exception as e:
                logger.error(f"[兼容层] 新服务查询失败，降级到旧服务: {e}", exc_info=True)
        return await self.old_service.get_user_messages(user_id, user_type, query)

    async def get_unread_count(self, user_id, user_type):
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        if tenant_id and await self._should_use_new(tenant_id):
            try:
                return await self.new_service.get_unread_count(user_id, user_type)
            except Exception as e:
                logger.error(f"[兼容层] 新服务查询失败，降级到旧服务: {e}", exc_info=True)
        return await self.old_service.get_unread_count(user_id, user_type)

    async def mark_as_read(self, message_id, user_id):
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        if tenant_id and await self._should_use_new(tenant_id):
            try:
                return await self.new_service.mark_as_read(message_id, user_id)
            except Exception as e:
                logger.error(f"[兼容层] 新服务操作失败，降级到旧服务: {e}", exc_info=True)
        return await self.old_service.mark_as_read(message_id, user_id)

    async def mark_all_as_read(self, user_id, user_type, message_type=None):
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        if tenant_id and await self._should_use_new(tenant_id):
            try:
                return await self.new_service.mark_all_as_read(user_id, user_type, message_type)
            except Exception as e:
                logger.error(f"[兼容层] 新服务操作失败，降级到旧服务: {e}", exc_info=True)
        return await self.old_service.mark_all_as_read(user_id, user_type, message_type)

    async def delete(self, message_id, user_id):
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        if tenant_id and await self._should_use_new(tenant_id):
            try:
                return await self.new_service.delete(message_id, user_id)
            except Exception as e:
                logger.error(f"[兼容层] 新服务删除失败，降级到旧服务: {e}", exc_info=True)
        return await self.old_service.delete(message_id, user_id)

    async def delete_all_read(self, user_id, user_type):
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        if tenant_id and await self._should_use_new(tenant_id):
            try:
                return await self.new_service.delete_all_read(user_id, user_type)
            except Exception as e:
                logger.error(f"[兼容层] 新服务批量删除失败，降级到旧服务: {e}", exc_info=True)
        return await self.old_service.delete_all_read(user_id, user_type)
