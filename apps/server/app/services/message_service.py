from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, and_
from typing import Optional, List
from datetime import datetime
import uuid
import json

from app.models.message import Message, MessageTemplate
from app.schemas.message import (
    MessageCreate, MessageBatchCreate, MessageQuery,
    MessageTemplateCreate, MessageTemplateUpdate, UnreadCountResponse
)


class MessageService:
    """消息服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, message_id: str) -> Optional[Message]:
        """根据ID获取消息"""
        result = await self.db.execute(
            select(Message).where(Message.id == message_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_messages(
        self, 
        user_id: str, 
        user_type: str,
        query: MessageQuery
    ) -> tuple[List[Message], int]:
        """获取用户消息列表"""
        stmt = select(Message).where(
            and_(Message.user_id == user_id, Message.user_type == user_type)
        )
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
    
    async def get_unread_count(self, user_id: str, user_type: str) -> UnreadCountResponse:
        """获取未读消息数量"""
        # 总未读数
        total_result = await self.db.execute(
            select(func.count(Message.id)).where(
                and_(
                    Message.user_id == user_id,
                    Message.user_type == user_type,
                    Message.is_read == 0
                )
            )
        )
        total = total_result.scalar() or 0
        
        # 各类型未读数
        type_counts = {}
        for msg_type in ['appointment', 'consultation', 'schedule', 'system', 'stop_clinic']:
            result = await self.db.execute(
                select(func.count(Message.id)).where(
                    and_(
                        Message.user_id == user_id,
                        Message.user_type == user_type,
                        Message.is_read == 0,
                        Message.message_type == msg_type
                    )
                )
            )
            type_counts[msg_type] = result.scalar() or 0
        
        return UnreadCountResponse(
            total=total,
            appointment=type_counts.get('appointment', 0),
            consultation=type_counts.get('consultation', 0),
            schedule=type_counts.get('schedule', 0),
            system=type_counts.get('system', 0),
            stop_clinic=type_counts.get('stop_clinic', 0)
        )
    
    async def create(self, data: MessageCreate) -> Message:
        """创建消息"""
        extra_data_str = json.dumps(data.extra_data) if data.extra_data else None
        
        message = Message(
            id=str(uuid.uuid4()),
            user_id=data.user_id,
            user_type=data.user_type,
            title=data.title,
            content=data.content,
            message_type=data.message_type.value,
            related_id=data.related_id,
            extra_data=extra_data_str
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message
    
    async def batch_create(self, data: MessageBatchCreate) -> int:
        """批量创建消息"""
        messages = []
        for user_id in data.user_ids:
            message = Message(
                id=str(uuid.uuid4()),
                user_id=user_id,
                user_type=data.user_type,
                title=data.title,
                content=data.content,
                message_type=data.message_type.value,
                related_id=data.related_id
            )
            messages.append(message)
        
        self.db.add_all(messages)
        await self.db.commit()
        return len(messages)
    
    async def mark_as_read(self, message_id: str, user_id: str) -> bool:
        """标记消息为已读"""
        result = await self.db.execute(
            update(Message)
            .where(and_(Message.id == message_id, Message.user_id == user_id))
            .values(is_read=1, read_at=datetime.utcnow())
        )
        await self.db.commit()
        return result.rowcount > 0
    
    async def mark_all_as_read(self, user_id: str, user_type: str, message_type: Optional[str] = None) -> int:
        """标记所有消息为已读"""
        stmt = update(Message).where(
            and_(
                Message.user_id == user_id,
                Message.user_type == user_type,
                Message.is_read == 0
            )
        )
        
        if message_type:
            stmt = stmt.where(Message.message_type == message_type)
        
        stmt = stmt.values(is_read=1, read_at=datetime.utcnow())
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount
    
    async def delete(self, message_id: str, user_id: str) -> bool:
        """删除消息"""
        message = await self.get_by_id(message_id)
        if not message or message.user_id != user_id:
            return False
        
        await self.db.delete(message)
        await self.db.commit()
        return True
    
    async def delete_all_read(self, user_id: str, user_type: str) -> int:
        """删除所有已读消息"""
        result = await self.db.execute(
            select(Message).where(
                and_(
                    Message.user_id == user_id,
                    Message.user_type == user_type,
                    Message.is_read == 1
                )
            )
        )
        messages = result.scalars().all()
        count = len(messages)
        
        for msg in messages:
            await self.db.delete(msg)
        
        await self.db.commit()
        return count
    
    # ========== 发送通知的便捷方法 ==========
    
    async def send_appointment_notification(
        self,
        user_id: str,
        user_type: str,
        title: str,
        content: str,
        appointment_id: str
    ) -> Message:
        """发送预约通知"""
        data = MessageCreate(
            user_id=user_id,
            user_type=user_type,
            title=title,
            content=content,
            message_type="appointment",
            related_id=appointment_id
        )
        return await self.create(data)
    
    async def send_schedule_notification(
        self,
        doctor_id: str,
        title: str,
        content: str,
        schedule_id: Optional[str] = None
    ) -> Message:
        """发送排班通知给医生"""
        data = MessageCreate(
            user_id=doctor_id,
            user_type="doctor",
            title=title,
            content=content,
            message_type="schedule",
            related_id=schedule_id
        )
        return await self.create(data)
    
    async def send_system_notification(
        self,
        user_id: str,
        user_type: str,
        title: str,
        content: str
    ) -> Message:
        """发送系统通知"""
        data = MessageCreate(
            user_id=user_id,
            user_type=user_type,
            title=title,
            content=content,
            message_type="system"
        )
        return await self.create(data)


class MessageTemplateService:
    """消息模板服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, template_id: str) -> Optional[MessageTemplate]:
        result = await self.db.execute(
            select(MessageTemplate).where(MessageTemplate.id == template_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_code(self, code: str) -> Optional[MessageTemplate]:
        result = await self.db.execute(
            select(MessageTemplate).where(MessageTemplate.code == code)
        )
        return result.scalar_one_or_none()
    
    async def get_list(self, status: Optional[int] = None) -> List[MessageTemplate]:
        stmt = select(MessageTemplate)
        if status is not None:
            stmt = stmt.where(MessageTemplate.status == status)
        stmt = stmt.order_by(MessageTemplate.created_at.desc())
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def create(self, data: MessageTemplateCreate) -> MessageTemplate:
        existing = await self.get_by_code(data.code)
        if existing:
            raise ValueError(f"模板编码 {data.code} 已存在")
        
        template = MessageTemplate(
            id=str(uuid.uuid4()),
            **data.model_dump()
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template
    
    async def update(self, template_id: str, data: MessageTemplateUpdate) -> Optional[MessageTemplate]:
        template = await self.get_by_id(template_id)
        if not template:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(template, field, value)
        
        await self.db.commit()
        await self.db.refresh(template)
        return template
    
    async def delete(self, template_id: str) -> bool:
        template = await self.get_by_id(template_id)
        if not template:
            return False
        
        await self.db.delete(template)
        await self.db.commit()
        return True
    
    def render_template(self, template: MessageTemplate, variables: dict) -> tuple[str, str]:
        """渲染模板"""
        title = template.title_template.format(**variables)
        content = template.content_template.format(**variables)
        return title, content
