from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_log import NotificationLog
from app.schemas.notification_log import (
    NotificationLogCreate,
    NotificationLogQuery,
    NotificationLogStats,
    NotificationStatus,
    NotificationChannel,
)


class NotificationLogService:
    """通知日志服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: NotificationLogCreate) -> NotificationLog:
        """创建通知日志记录（轻量级，同步调用）"""
        log = NotificationLog(
            channel=data.channel.value,
            message_type=data.message_type,
            title=data.title,
            content=data.content,
            recipient=data.recipient,
            user_id=data.user_id,
            user_type=data.user_type,
            related_id=data.related_id,
            tenant_id=data.tenant_id,
            store_id=data.store_id,
            extra_data=data.extra_data,
            status=NotificationStatus.PENDING.value,
            retry_count=0,
            created_at=datetime.utcnow(),
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def get_list(
        self, query: NotificationLogQuery
    ) -> Tuple[List[NotificationLog], int]:
        """分页查询通知日志"""
        stmt = select(NotificationLog)
        count_stmt = select(func.count(NotificationLog.id))

        conditions = []
        if query.channel:
            conditions.append(NotificationLog.channel == query.channel.value)
        if query.status:
            conditions.append(NotificationLog.status == query.status.value)
        if query.message_type:
            conditions.append(NotificationLog.message_type == query.message_type)
        if query.user_id:
            conditions.append(NotificationLog.user_id == query.user_id)
        if query.store_id:
            conditions.append(NotificationLog.store_id == query.store_id)
        if query.start_date:
            conditions.append(NotificationLog.created_at >= query.start_date)
        if query.end_date:
            conditions.append(NotificationLog.created_at <= query.end_date)

        if conditions:
            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))

        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.order_by(NotificationLog.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)

        result = await self.db.execute(stmt)
        logs = result.scalars().all()

        return list(logs), total

    async def get_stats(
        self,
        store_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> NotificationLogStats:
        """获取通知统计信息"""
        base_conditions = []
        if store_id:
            base_conditions.append(NotificationLog.store_id == store_id)
        if start_date:
            base_conditions.append(NotificationLog.created_at >= start_date)
        if end_date:
            base_conditions.append(NotificationLog.created_at <= end_date)

        total_result = await self.db.execute(
            select(func.count(NotificationLog.id)).where(and_(*base_conditions))
            if base_conditions
            else select(func.count(NotificationLog.id))
        )
        total = total_result.scalar() or 0

        status_conditions = base_conditions.copy() if base_conditions else []

        sent_result = await self.db.execute(
            select(func.count(NotificationLog.id)).where(
                and_(*status_conditions, NotificationLog.status == NotificationStatus.SENT.value)
            )
            if status_conditions
            else select(func.count(NotificationLog.id)).where(
                NotificationLog.status == NotificationStatus.SENT.value
            )
        )
        sent = sent_result.scalar() or 0

        failed_result = await self.db.execute(
            select(func.count(NotificationLog.id)).where(
                and_(*status_conditions, NotificationLog.status == NotificationStatus.FAILED.value)
            )
            if status_conditions
            else select(func.count(NotificationLog.id)).where(
                NotificationLog.status == NotificationStatus.FAILED.value
            )
        )
        failed = failed_result.scalar() or 0

        pending_result = await self.db.execute(
            select(func.count(NotificationLog.id)).where(
                and_(*status_conditions, NotificationLog.status == NotificationStatus.PENDING.value)
            )
            if status_conditions
            else select(func.count(NotificationLog.id)).where(
                NotificationLog.status == NotificationStatus.PENDING.value
            )
        )
        pending = pending_result.scalar() or 0

        failure_rate = (failed / total * 100) if total > 0 else 0.0

        by_channel_result = await self.db.execute(
            select(NotificationLog.channel, func.count(NotificationLog.id))
            .where(and_(*base_conditions) if base_conditions else True)
            .group_by(NotificationLog.channel)
            if base_conditions
            else select(NotificationLog.channel, func.count(NotificationLog.id)).group_by(
                NotificationLog.channel
            )
        )
        by_channel = {channel: count for channel, count in by_channel_result.all()}

        by_type_result = await self.db.execute(
            select(NotificationLog.message_type, func.count(NotificationLog.id))
            .where(and_(*base_conditions) if base_conditions else True)
            .group_by(NotificationLog.message_type)
            if base_conditions
            else select(NotificationLog.message_type, func.count(NotificationLog.id)).group_by(
                NotificationLog.message_type
            )
        )
        by_type = {msg_type: count for msg_type, count in by_type_result.all()}

        return NotificationLogStats(
            total=total,
            sent=sent,
            failed=failed,
            pending=pending,
            failure_rate=failure_rate,
            by_channel=by_channel,
            by_type=by_type,
        )

    async def mark_sent(self, log_id: str) -> bool:
        """标记为已发送"""
        result = await self.db.execute(
            update(NotificationLog)
            .where(NotificationLog.id == log_id)
            .values(status=NotificationStatus.SENT.value, sent_at=datetime.utcnow())
        )
        await self.db.commit()
        return result.rowcount > 0

    async def mark_failed(self, log_id: str, error_message: str, increment_retry: bool = True) -> bool:
        """标记为失败并记录错误信息"""
        values = {
            "status": NotificationStatus.FAILED.value,
            "error_message": error_message,
        }
        if increment_retry:
            values["retry_count"] = NotificationLog.retry_count + 1  # SQL-level increment

        stmt = update(NotificationLog).where(NotificationLog.id == log_id).values(**values)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def get_by_id(self, log_id: str) -> Optional[NotificationLog]:
        """根据ID获取日志"""
        result = await self.db.execute(select(NotificationLog).where(NotificationLog.id == log_id))
        return result.scalar_one_or_none()
