"""Message delivery and inbox service."""

import json
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, func, select, update

from app.models.message import Message
from app.schemas.message import MessageBatchCreate, MessageCreate, MessageQuery, MessageType, UnreadCountResponse
from app.utils.audit import set_create_audit


class MessageService:
    def __init__(self, db):
        self.db = db

    async def get_by_id(self, message_id: str) -> Optional[Message]:
        result = await self.db.execute(select(Message).where(Message.id == message_id))
        return result.scalar_one_or_none()

    async def get_user_messages(
        self, user_id: str, user_type: str, query: MessageQuery
    ) -> tuple[List[Message], int]:
        stmt = select(Message).where(and_(Message.user_id == user_id, Message.user_type == user_type))
        count_stmt = select(func.count(Message.id)).where(
            and_(Message.user_id == user_id, Message.user_type == user_type)
        )

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
        total_result = await self.db.execute(
            select(func.count(Message.id)).where(
                and_(Message.user_id == user_id, Message.user_type == user_type, Message.is_read == 0)
            )
        )
        total = total_result.scalar() or 0

        type_counts = {}
        for msg_type in ["appointment", "consultation", "schedule", "system", "stop_clinic", "feedback"]:
            result = await self.db.execute(
                select(func.count(Message.id)).where(
                    and_(
                        Message.user_id == user_id,
                        Message.user_type == user_type,
                        Message.is_read == 0,
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
        message = Message(
            id=str(uuid.uuid4()),
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
        return message

    async def batch_create(
        self, data: MessageBatchCreate, store_id: Optional[str] = None, operator_id: Optional[str] = None
    ) -> int:
        messages = []
        for user_id in data.user_ids:
            message = Message(
                id=str(uuid.uuid4()),
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
        result = await self.db.execute(
            select(Message).where(
                and_(Message.user_id == user_id, Message.user_type == user_type, Message.is_read == 1)
            )
        )
        messages = result.scalars().all()
        count = len(messages)
        for msg in messages:
            await self.db.delete(msg)
        await self.db.commit()
        return count

    async def send_appointment_notification(
        self, user_id: str, user_type: str, title: str, content: str, appointment_id: str
    ) -> Message:
        data = MessageCreate(
            user_id=user_id,
            user_type=user_type,
            title=title,
            content=content,
            message_type=MessageType.APPOINTMENT,
            related_id=appointment_id,
        )
        return await self.create(data)

    async def send_schedule_notification(
        self, doctor_id: str, title: str, content: str, schedule_id: Optional[str] = None
    ) -> Message:
        data = MessageCreate(
            user_id=doctor_id,
            user_type="doctor",
            title=title,
            content=content,
            message_type=MessageType.SCHEDULE,
            related_id=schedule_id,
        )
        return await self.create(data)

    async def send_system_notification(
        self, user_id: str, user_type: str, title: str, content: str
    ) -> Message:
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
    ) -> Message:
        data = MessageCreate(
            user_id=user_id,
            user_type=user_type,
            title=title,
            content=content,
            message_type=MessageType.STOP_CLINIC,
            related_id=appointment_id,
        )
        return await self.create(data)
