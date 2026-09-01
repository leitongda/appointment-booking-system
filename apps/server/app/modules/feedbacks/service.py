import json
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id
from app.models.feedback import Feedback, FeedbackStatus
from app.models.message import Message, MessageType
from app.schemas.feedback import FeedbackCreate, FeedbackQuery, FeedbackReply
from app.utils.audit import set_create_audit, set_update_audit


class FeedbackService:
    """用户反馈服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _tenant_filter(self, stmt):
        """为查询添加租户过滤"""
        tenant_id = get_current_tenant_id()
        if tenant_id:
            return stmt.where(Feedback.tenant_id == tenant_id)
        return stmt

    async def get_by_id(self, feedback_id: str) -> Feedback | None:
        """根据ID获取反馈"""
        stmt = self._tenant_filter(
            select(Feedback).where(Feedback.id == feedback_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_list(self, query: FeedbackQuery) -> tuple[list[Feedback], int]:
        """获取反馈列表"""
        stmt = self._tenant_filter(select(Feedback))
        count_stmt = self._tenant_filter(select(func.count(Feedback.id)))

        if query.user_id:
            stmt = stmt.where(Feedback.user_id == query.user_id)
            count_stmt = count_stmt.where(Feedback.user_id == query.user_id)

        if query.feedback_type:
            stmt = stmt.where(Feedback.feedback_type == query.feedback_type.value)
            count_stmt = count_stmt.where(Feedback.feedback_type == query.feedback_type.value)

        if query.status:
            stmt = stmt.where(Feedback.status == query.status.value)
            count_stmt = count_stmt.where(Feedback.status == query.status.value)

        if query.keyword:
            keyword_filter = Feedback.title.contains(query.keyword) | Feedback.content.contains(query.keyword)
            stmt = stmt.where(keyword_filter)
            count_stmt = count_stmt.where(keyword_filter)

        stmt = stmt.order_by(Feedback.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)

        result = await self.db.execute(stmt)
        count_result = await self.db.execute(count_stmt)

        return list(result.scalars().all()), count_result.scalar() or 0

    async def get_user_feedbacks(self, user_id: str) -> list[Feedback]:
        """获取用户的反馈列表"""
        stmt = self._tenant_filter(
            select(Feedback)
            .where(Feedback.user_id == user_id)
            .order_by(Feedback.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, data: FeedbackCreate) -> Feedback:
        """创建反馈"""
        images_str = json.dumps(data.images) if data.images else None
        feedback_type = getattr(data.feedback_type, "value", data.feedback_type)

        feedback = Feedback(
            id=str(uuid.uuid4()),
            tenant_id=get_current_tenant_id(),
            user_id=data.user_id,
            user_type=data.user_type,
            feedback_type=feedback_type,
            title=data.title,
            content=data.content,
            images=images_str,
            contact=data.contact
        )
        set_create_audit(feedback, data.user_id)

        self.db.add(feedback)
        await self.db.commit()
        await self.db.refresh(feedback)
        return feedback

    async def reply(
        self,
        feedback_id: str,
        handler_id: str,
        data: FeedbackReply
    ) -> Feedback | None:
        """回复反馈"""
        feedback = await self.get_by_id(feedback_id)
        if not feedback:
            return None

        feedback.reply = data.reply
        feedback.status = data.status.value
        feedback.handler_id = handler_id
        feedback.handled_at = datetime.utcnow()
        set_update_audit(feedback, handler_id)

        # 创建消息通知给用户
        message = Message(
            id=str(uuid.uuid4()),
            tenant_id=feedback.tenant_id,
            user_id=feedback.user_id,
            user_type=feedback.user_type or "patient",
            title="您的反馈已收到回复",
            content=f"您提交的反馈「{feedback.title}」已收到回复：{data.reply[:100]}{'...' if len(data.reply) > 100 else ''}",
            message_type=MessageType.FEEDBACK.value,
            related_id=feedback_id,
        )
        set_create_audit(message, handler_id)
        self.db.add(message)

        await self.db.commit()
        await self.db.refresh(feedback)
        return feedback

    async def update_status(
        self,
        feedback_id: str,
        status: str,
        operator_id: str | None = None
    ) -> Feedback | None:
        """更新状态"""
        feedback = await self.get_by_id(feedback_id)
        if not feedback:
            return None

        feedback.status = status
        set_update_audit(feedback, operator_id)
        await self.db.commit()
        await self.db.refresh(feedback)
        return feedback

    async def delete(self, feedback_id: str) -> bool:
        """删除反馈"""
        feedback = await self.get_by_id(feedback_id)
        if not feedback:
            return False

        await self.db.delete(feedback)
        await self.db.commit()
        return True

    async def get_pending_count(self) -> int:
        """获取待处理数量"""
        stmt = self._tenant_filter(
            select(func.count(Feedback.id)).where(
                Feedback.status == FeedbackStatus.PENDING.value
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_statistics(self) -> dict:
        """获取反馈统计"""
        tenant_id = get_current_tenant_id()

        # 总数
        total_stmt = select(func.count(Feedback.id))
        if tenant_id:
            total_stmt = total_stmt.where(Feedback.tenant_id == tenant_id)
        total_result = await self.db.execute(total_stmt)
        total = total_result.scalar() or 0

        # 各状态数量
        status_counts = {}
        for status in ['pending', 'processing', 'resolved', 'closed']:
            stmt = select(func.count(Feedback.id)).where(Feedback.status == status)
            if tenant_id:
                stmt = stmt.where(Feedback.tenant_id == tenant_id)
            result = await self.db.execute(stmt)
            status_counts[status] = result.scalar() or 0

        # 各类型数量
        type_counts = {}
        for fb_type in ['suggestion', 'complaint', 'bug', 'other']:
            stmt = select(func.count(Feedback.id)).where(Feedback.feedback_type == fb_type)
            if tenant_id:
                stmt = stmt.where(Feedback.tenant_id == tenant_id)
            result = await self.db.execute(stmt)
            type_counts[fb_type] = result.scalar() or 0

        return {
            'total': total,
            'by_status': status_counts,
            'by_type': type_counts
        }
