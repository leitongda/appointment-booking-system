"""Message delivery and inbox service.

.. deprecated::
    此模块已被 unified_message 替代。新代码应使用 UnifiedMessageService 或 MessageServiceCompat。
    保留此文件仅为向后兼容，不再主动调用。
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, NamedTuple, Optional, Tuple

logger = logging.getLogger(__name__)

from sqlalchemy import and_, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.models.notification_log import NotificationLog
from app.models.user import User
from app.schemas.message import MessageBatchCreate, MessageCreate, MessageQuery, MessageType, UnreadCountResponse
from app.schemas.notification import NotificationEvent, NotificationContent
from app.utils.audit import set_create_audit
from app.middleware.tenant_context import get_current_tenant_id
from app.infrastructure.sms.service import SmsService
from app.infrastructure.notifications.dispatcher import NotificationDispatcher


# ---------------------------------------------------------------------------
# 统一账号辅助：Account 表优先 + 旧表 fallback
# ---------------------------------------------------------------------------

class ContactInfo(NamedTuple):
    """用户联系方式"""
    phone: Optional[str]
    openid: Optional[str]
    email: Optional[str]


async def _get_user_contact_info(db: AsyncSession, user_id: str) -> ContactInfo:
    """获取用户联系方式 (phone, openid, email)，Account 表优先"""
    try:
        from app.models.account import Account, AccountUser
        result = await db.execute(
            select(Account.phone, AccountUser.openid, Account.email)
            .join(AccountUser, Account.id == AccountUser.account_id, isouter=True)
            .where(Account.id == user_id)
        )
        row = result.first()
        if row and row[0]:
            return ContactInfo(phone=row[0], openid=row[1], email=row[2])
    except Exception:
        pass

    # fallback 到旧表
    user_result = await db.execute(
        select(User.phone, User.openid, User.email).where(User.id == user_id)
    )
    user_info = user_result.first()
    if user_info:
        return ContactInfo(phone=user_info[0], openid=user_info[1], email=user_info[2])
    return ContactInfo(None, None, None)


from app.common.notification_preference import check_notification_preference as _check_preference


async def _send_sms_notification(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    message_type: str,
    template_variables: Dict[str, str],
    related_id: Optional[str] = None,
) -> bool:
    """
    发送短信通知（辅助函数）

    Args:
        db: 数据库会话
        tenant_id: 租户ID
        user_id: 用户ID
        message_type: 消息类型（appointment_success/appointment_reminder/appointment_cancelled/stop_clinic）
        template_variables: 模板变量
        related_id: 关联业务ID

    Returns:
        是否发送成功
    """
    try:
        # 检查短信偏好
        if not await _check_preference(db, user_id, "patient", "sms", message_type):
            logger.debug(f"用户 {user_id} 已禁用 sms/{message_type} 通知，跳过")
            return False

        # 获取用户手机号（Account 表优先）
        user_phone, _, _ = await _get_user_contact_info(db, user_id)

        if not user_phone:
            logger.debug(f"用户 {user_id} 无手机号，跳过短信发送")
            return False

        # 根据消息类型调用对应的 SmsService 方法
        sms_method_map = {
            "appointment_success": SmsService.send_appointment_success,
            "appointment_reminder": SmsService.send_appointment_reminder,
            "appointment_cancelled": SmsService.send_appointment_cancelled,
            "stop_clinic": SmsService.send_stop_clinic_notice,
        }

        sms_method = sms_method_map.get(message_type)
        if not sms_method:
            logger.warning(f"未知的短信消息类型: {message_type}")
            return False

        return await sms_method(
            tenant_id=tenant_id,
            phone=user_phone,
            variables=template_variables,
            user_id=user_id,
            related_id=related_id,
        )

    except Exception as e:
        logger.error(f"短信通知发送失败: user_id={user_id}, type={message_type}, error={e}")
        return False


class MessageService:
    def __init__(self, db):
        self.db = db
        self._dispatcher: Optional[NotificationDispatcher] = None

    @property
    def dispatcher(self) -> NotificationDispatcher:
        """获取通知分发器实例（延迟初始化）"""
        if self._dispatcher is None:
            self._dispatcher = NotificationDispatcher(self.db)
        return self._dispatcher

    async def _render_from_template(self, code: str, variables: dict) -> Tuple[Optional[str], Optional[str]]:
        """从模板渲染标题和内容，返回 (title, content)。

        模板不存在或禁用时返回 (None, None)，由调用方使用 fallback。
        """
        try:
            from app.modules.messages.service_templates import MessageTemplateService

            template_service = MessageTemplateService(self.db)
            template = await template_service.get_by_code(code)
            if not template or template.status != 1:
                return None, None

            title, content = template_service.render_template(template, variables)
            return title, content
        except Exception as e:
            logger.warning(f"模板渲染失败 (code={code}): {e}")
            return None, None

    async def get_by_id(self, message_id: str) -> Optional[Message]:
        stmt = select(Message).where(Message.id == message_id)
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(Message.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_messages(
        self, user_id: str, user_type: str, query: MessageQuery
    ) -> tuple[List[Message], int]:
        stmt = select(Message).where(and_(Message.user_id == user_id, Message.user_type == user_type))
        count_stmt = select(func.count(Message.id)).where(
            and_(Message.user_id == user_id, Message.user_type == user_type)
        )

        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(Message.tenant_id == tenant_id)
            count_stmt = count_stmt.where(Message.tenant_id == tenant_id)

        if query.message_type:
            stmt = stmt.where(Message.message_type == query.message_type.value)
            count_stmt = count_stmt.where(Message.message_type == query.message_type.value)
        if query.is_read is not None:
            stmt = stmt.where(Message.is_read == query.is_read)
            count_stmt = count_stmt.where(Message.is_read == query.is_read)

        stmt = stmt.order_by(Message.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        result = await self.db.execute(stmt)
        count_result = await self.db.execute(count_stmt)
        return list(result.scalars().all()), count_result.scalar() or 0

    async def get_all_messages(
        self,
        user_id: Optional[str],
        user_type: Optional[str],
        keyword: Optional[str],
        query: MessageQuery,
        store_id: Optional[str] = None,
    ) -> tuple[List[Message], int]:
        stmt = select(Message)
        count_stmt = select(func.count(Message.id))

        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(Message.tenant_id == tenant_id)
            count_stmt = count_stmt.where(Message.tenant_id == tenant_id)

        if user_id:
            stmt = stmt.where(Message.user_id == user_id)
            count_stmt = count_stmt.where(Message.user_id == user_id)
        if user_type:
            stmt = stmt.where(Message.user_type == user_type)
            count_stmt = count_stmt.where(Message.user_type == user_type)
        if query.message_type:
            stmt = stmt.where(Message.message_type == query.message_type.value)
            count_stmt = count_stmt.where(Message.message_type == query.message_type.value)
        if query.is_read is not None:
            stmt = stmt.where(Message.is_read == query.is_read)
            count_stmt = count_stmt.where(Message.is_read == query.is_read)
        if keyword:
            keyword_filter = Message.title.contains(keyword) | Message.content.contains(keyword)
            stmt = stmt.where(keyword_filter)
            count_stmt = count_stmt.where(keyword_filter)
        if store_id:
            from sqlalchemy import or_

            store_filter = or_(Message.store_id == store_id, Message.store_id.is_(None))
            stmt = stmt.where(store_filter)
            count_stmt = count_stmt.where(store_filter)

        stmt = stmt.order_by(Message.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        result = await self.db.execute(stmt)
        count_result = await self.db.execute(count_stmt)
        return list(result.scalars().all()), count_result.scalar() or 0

    async def get_unread_count(self, user_id: str, user_type: str) -> UnreadCountResponse:
        tenant_id = get_current_tenant_id()
        base_condition = and_(Message.user_id == user_id, Message.user_type == user_type, Message.is_read == 0)
        if tenant_id:
            base_condition = and_(base_condition, Message.tenant_id == tenant_id)

        total_result = await self.db.execute(
            select(func.count(Message.id)).where(base_condition)
        )
        total = total_result.scalar() or 0

        type_counts = {}
        for msg_type in ["appointment", "consultation", "schedule", "system", "stop_clinic", "feedback"]:
            result = await self.db.execute(
                select(func.count(Message.id)).where(
                    and_(
                        base_condition,
                        Message.message_type == msg_type,
                    )
                )
            )
            type_counts[msg_type] = result.scalar() or 0

        return UnreadCountResponse(
            total=total,
            appointment=type_counts.get("appointment", 0),
            consultation=type_counts.get("consultation", 0),
            schedule=type_counts.get("schedule", 0),
            system=type_counts.get("system", 0),
            stop_clinic=type_counts.get("stop_clinic", 0),
            feedback=type_counts.get("feedback", 0),
        )

    async def create(
        self, data: MessageCreate, store_id: Optional[str] = None, operator_id: Optional[str] = None
    ) -> Message:
        extra_data_str = json.dumps(data.extra_data) if data.extra_data else None
        tenant_id = get_current_tenant_id()
        message = Message(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            store_id=store_id,
            user_id=data.user_id,
            user_type=data.user_type,
            title=data.title,
            content=data.content,
            message_type=data.message_type.value,
            related_id=data.related_id,
            extra_data=extra_data_str,
        )
        set_create_audit(message, operator_id)
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)

        try:
            log = NotificationLog(
                tenant_id=tenant_id,
                store_id=store_id,
                user_id=data.user_id,
                user_type=data.user_type,
                channel="in_app",
                message_type=data.message_type.value,
                title=data.title,
                content=data.content,
                status="sent",
                recipient=f"{data.user_type}:{data.user_id}",
                related_id=data.related_id,
                sent_at=datetime.utcnow(),
            )
            self.db.add(log)
            await self.db.commit()
        except Exception as e:
            logger.error(f"创建通知日志失败: {e}")

        return message

    async def batch_create(
        self, data: MessageBatchCreate, store_id: Optional[str] = None, operator_id: Optional[str] = None
    ) -> int:
        messages = []
        logs = []
        tenant_id = get_current_tenant_id()
        for user_id in data.user_ids:
            message = Message(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                store_id=store_id,
                user_id=user_id,
                user_type=data.user_type,
                title=data.title,
                content=data.content,
                message_type=data.message_type.value,
                related_id=data.related_id,
            )
            set_create_audit(message, operator_id)
            messages.append(message)

        self.db.add_all(messages)
        await self.db.commit()

        try:
            for user_id in data.user_ids:
                logs.append(NotificationLog(
                    tenant_id=tenant_id,
                    store_id=store_id,
                    user_id=user_id,
                    user_type=data.user_type,
                    channel="in_app",
                    message_type=data.message_type.value,
                    title=data.title,
                    content=data.content,
                    status="sent",
                    recipient=f"{data.user_type}:{user_id}",
                    related_id=data.related_id,
                    sent_at=datetime.utcnow(),
                ))
            self.db.add_all(logs)
            await self.db.commit()
        except Exception as e:
            logger.error(f"批量创建通知日志失败: {e}")

        return len(messages)

    async def mark_as_read(self, message_id: str, user_id: str) -> bool:
        result = await self.db.execute(
            update(Message)
            .where(and_(Message.id == message_id, Message.user_id == user_id))
            .values(is_read=1, read_at=datetime.utcnow())
        )
        await self.db.commit()
        return result.rowcount > 0

    async def mark_all_as_read(
        self, user_id: str, user_type: str, message_type: Optional[str] = None
    ) -> int:
        stmt = update(Message).where(
            and_(Message.user_id == user_id, Message.user_type == user_type, Message.is_read == 0)
        )
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(Message.tenant_id == tenant_id)
        if message_type:
            stmt = stmt.where(Message.message_type == message_type)
        stmt = stmt.values(is_read=1, read_at=datetime.utcnow())
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def delete(self, message_id: str, user_id: str) -> bool:
        message = await self.get_by_id(message_id)
        if not message or message.user_id != user_id:
            return False
        await self.db.delete(message)
        await self.db.commit()
        return True

    async def delete_all_read(self, user_id: str, user_type: str) -> int:
        stmt = select(Message).where(
            and_(Message.user_id == user_id, Message.user_type == user_type, Message.is_read == 1)
        )
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(Message.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        count = len(messages)
        for msg in messages:
            await self.db.delete(msg)
        await self.db.commit()
        return count

    _TITLE_TEMPLATE_CODE_MAP = {
        "预约成功": "appointment_success",
        "就诊提醒": "appointment_remind",
        "叫号通知": "queue_call",
        "预约已取消": "appointment_cancelled",
    }

    async def send_appointment_notification(
        self, user_id: str, user_type: str, title: str, content: str, appointment_id: str,
        template_code: Optional[str] = None, template_variables: Optional[dict] = None,
    ) -> Optional[Message]:
        """发送预约通知（向后兼容方法）

        内部使用 NotificationDispatcher 进行统一分发。
        """
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            logger.warning("缺少租户上下文，无法发送通知")
            return None

        # 确定消息类型
        message_type_map = {
            "预约成功": "appointment_success",
            "就诊提醒": "appointment_reminder",
            "叫号通知": "queue_call",
            "预约已取消": "appointment_cancelled",
        }
        message_type = message_type_map.get(title, "appointment")

        # 渲染模板
        rendered_title, rendered_content = title, content
        code = template_code or self._TITLE_TEMPLATE_CODE_MAP.get(title)
        if code and template_variables:
            rendered_title, rendered_content = await self._render_from_template(
                code, template_variables
            )
            if rendered_title is None:
                rendered_title, rendered_content = title, content

        # 获取接收人信息（Account 表优先）
        contact = await _get_user_contact_info(self.db, user_id)

        # 创建通知事件
        event = NotificationEvent(
            tenant_id=tenant_id,
            recipient_id=user_id,
            recipient_type=user_type,
            recipient_phone=contact.phone,
            recipient_openid=contact.openid,
            recipient_email=contact.email,
            template_code=code or message_type,
            variables=template_variables or {},
            message_type=message_type,
            related_id=appointment_id,
            title=rendered_title,
            content=rendered_content,
        )

        # 使用分发器发送
        dispatch_result = await self.dispatcher.dispatch(event)

        # 返回站内信 Message（向后兼容）
        in_app_result = dispatch_result.results.get("in_app")
        if in_app_result and in_app_result.success:
            # 查询创建的 Message
            msg_result = await self.db.execute(
                select(Message).where(
                    and_(
                        Message.user_id == user_id,
                        Message.related_id == appointment_id,
                        Message.message_type == MessageType.APPOINTMENT.value,
                    )
                ).order_by(Message.created_at.desc()).limit(1)
            )
            return msg_result.scalar_one_or_none()

        return None

    async def send_schedule_notification(
        self, doctor_id: str, title: str, content: str, schedule_id: Optional[str] = None,
        template_code: Optional[str] = None, template_variables: Optional[dict] = None,
    ) -> Optional[Message]:
        """发送排班通知（向后兼容方法）

        内部使用 NotificationDispatcher 进行统一分发。
        """
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            logger.warning("缺少租户上下文，无法发送通知")
            return None

        # 渲染模板
        rendered_title, rendered_content = title, content
        if template_code and template_variables:
            rendered_title, rendered_content = await self._render_from_template(
                template_code, template_variables
            )
            if rendered_title is None:
                rendered_title, rendered_content = title, content

        # 创建通知事件
        event = NotificationEvent(
            tenant_id=tenant_id,
            recipient_id=doctor_id,
            recipient_type="doctor",
            template_code=template_code or "schedule",
            variables=template_variables or {},
            message_type="schedule",
            related_id=schedule_id,
            title=rendered_title,
            content=rendered_content,
        )

        # 使用分发器发送
        dispatch_result = await self.dispatcher.dispatch(event)

        # 返回站内信 Message（向后兼容）
        in_app_result = dispatch_result.results.get("in_app")
        if in_app_result and in_app_result.success:
            msg_result = await self.db.execute(
                select(Message).where(
                    and_(
                        Message.user_id == doctor_id,
                        Message.related_id == schedule_id if schedule_id else True,
                        Message.message_type == MessageType.SCHEDULE.value,
                    )
                ).order_by(Message.created_at.desc()).limit(1)
            )
            return msg_result.scalar_one_or_none()

        return None

    async def send_system_notification(
        self, user_id: str, user_type: str, title: str, content: str
    ) -> Message:
        """发送系统通知（向后兼容方法）

        内部使用 NotificationDispatcher 进行统一分发。
        """
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            logger.warning("缺少租户上下文，无法发送通知")
            # 降级：直接创建站内信
            data = MessageCreate(
                user_id=user_id,
                user_type=user_type,
                title=title,
                content=content,
                message_type=MessageType.SYSTEM,
            )
            return await self.create(data)

        # 创建通知事件
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

        # 使用分发器发送
        dispatch_result = await self.dispatcher.dispatch(event)

        # 返回站内信 Message（向后兼容）
        in_app_result = dispatch_result.results.get("in_app")
        if in_app_result and in_app_result.success:
            msg_result = await self.db.execute(
                select(Message).where(
                    and_(
                        Message.user_id == user_id,
                        Message.user_type == user_type,
                        Message.message_type == MessageType.SYSTEM.value,
                        Message.title == title,
                    )
                ).order_by(Message.created_at.desc()).limit(1)
            )
            message = msg_result.scalar_one_or_none()
            if message:
                return message

        # 降级：直接创建站内信
        data = MessageCreate(
            user_id=user_id,
            user_type=user_type,
            title=title,
            content=content,
            message_type=MessageType.SYSTEM,
        )
        return await self.create(data)

    async def send_stop_clinic_notification(
        self,
        user_id: str,
        user_type: str,
        title: str,
        content: str,
        appointment_id: Optional[str] = None,
        template_code: Optional[str] = None,
        template_variables: Optional[dict] = None,
    ) -> Optional[Message]:
        """发送停诊通知（向后兼容方法）

        内部使用 NotificationDispatcher 进行统一分发。
        """
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            logger.warning("缺少租户上下文，无法发送通知")
            return None

        # 渲染模板
        rendered_title, rendered_content = title, content
        code = template_code or "stop_clinic_patient"
        if code and template_variables:
            rendered_title, rendered_content = await self._render_from_template(
                code, template_variables
            )
            if rendered_title is None:
                rendered_title, rendered_content = title, content

        # 获取接收人信息（Account 表优先）
        contact = await _get_user_contact_info(self.db, user_id)

        # 创建通知事件
        event = NotificationEvent(
            tenant_id=tenant_id,
            recipient_id=user_id,
            recipient_type=user_type,
            recipient_phone=contact.phone,
            recipient_openid=contact.openid,
            recipient_email=contact.email,
            template_code=code,
            variables=template_variables or {},
            message_type="stop_clinic",
            related_id=appointment_id,
            title=rendered_title,
            content=rendered_content,
        )

        # 使用分发器发送
        dispatch_result = await self.dispatcher.dispatch(event)

        # 返回站内信 Message（向后兼容）
        in_app_result = dispatch_result.results.get("in_app")
        if in_app_result and in_app_result.success:
            msg_result = await self.db.execute(
                select(Message).where(
                    and_(
                        Message.user_id == user_id,
                        Message.related_id == appointment_id if appointment_id else True,
                        Message.message_type == MessageType.STOP_CLINIC.value,
                    )
                ).order_by(Message.created_at.desc()).limit(1)
            )
            return msg_result.scalar_one_or_none()

        return None
