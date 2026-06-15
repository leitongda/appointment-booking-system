from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_log import NotificationLog
from app.schemas.notification_log import (
    NotificationLogCreate,
    NotificationLogQuery,
    NotificationLogStats,
    NotificationStatus,
)


def calculate_next_retry(retry_count: int) -> datetime | None:
    """计算下次重试时间（指数退避策略）

    Args:
        retry_count: 当前重试次数

    Returns:
        下次重试时间，如果超过最大重试次数返回 None
    """
    delays = [1, 5, 30]  # 分钟：1分钟 -> 5分钟 -> 30分钟
    if retry_count >= len(delays):
        return None
    delay = delays[retry_count]
    return datetime.utcnow() + timedelta(minutes=delay)


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
    ) -> tuple[list[NotificationLog], int]:
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
        store_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
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
        """标记为失败并记录错误信息

        Args:
            log_id: 通知日志ID
            error_message: 错误信息
            increment_retry: 是否增加重试计数

        Returns:
            是否更新成功
        """
        # 先获取当前记录
        log = await self.get_by_id(log_id)
        if not log:
            return False

        values = {
            "status": NotificationStatus.FAILED.value,
            "error_message": error_message,
        }
        if increment_retry:
            new_retry_count = log.retry_count + 1
            values["retry_count"] = new_retry_count

            # 计算下次重试时间
            next_retry = calculate_next_retry(new_retry_count)
            if next_retry:
                values["next_retry_at"] = next_retry
            else:
                # 超过最大重试次数，标记为永久失败
                values["status"] = NotificationStatus.PERMANENTLY_FAILED.value

        stmt = update(NotificationLog).where(NotificationLog.id == log_id).values(**values)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def get_by_id(self, log_id: str) -> NotificationLog | None:
        """根据ID获取日志"""
        result = await self.db.execute(select(NotificationLog).where(NotificationLog.id == log_id))
        return result.scalar_one_or_none()

    async def get_usage_stats(
        self,
        tenant_id: str,
        period: str = "month",
        group_by: str = "channel",
    ) -> dict[str, Any]:
        """获取租户通知用量统计

        Args:
            tenant_id: 租户ID
            period: 统计周期 (day/week/month)
            group_by: 分组维度 (channel/type/status)

        Returns:
            统计数据字典：
            {
                "period": {"start": ..., "end": ...},
                "total": 1234,
                "by_channel": {"sms": 100, "email": 200, "wechat": 500, "in_app": 434},
                "by_type": {"appointment": 300, ...},
                "by_status": {"sent": 1200, "failed": 34},
                "daily_trend": [{"date": "2024-01-01", "count": 50}, ...]
            }
        """
        now = datetime.utcnow()

        # 计算时间范围
        if period == "day":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period == "week":
            start_date = now - timedelta(days=7)
            end_date = now
        else:  # month
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now

        # 基础条件
        base_conditions = [
            NotificationLog.tenant_id == tenant_id,
            NotificationLog.created_at >= start_date,
            NotificationLog.created_at <= end_date,
        ]

        # 总数统计
        total_result = await self.db.execute(
            select(func.count(NotificationLog.id)).where(and_(*base_conditions))
        )
        total = total_result.scalar() or 0

        # 按渠道统计
        by_channel_result = await self.db.execute(
            select(NotificationLog.channel, func.count(NotificationLog.id))
            .where(and_(*base_conditions))
            .group_by(NotificationLog.channel)
        )
        by_channel = {channel: count for channel, count in by_channel_result.all()}

        # 按类型统计
        by_type_result = await self.db.execute(
            select(NotificationLog.message_type, func.count(NotificationLog.id))
            .where(and_(*base_conditions))
            .group_by(NotificationLog.message_type)
        )
        by_type = {msg_type: count for msg_type, count in by_type_result.all()}

        # 按状态统计
        by_status_result = await self.db.execute(
            select(NotificationLog.status, func.count(NotificationLog.id))
            .where(and_(*base_conditions))
            .group_by(NotificationLog.status)
        )
        by_status = {status: count for status, count in by_status_result.all()}

        # 每日趋势
        daily_trend = []
        if period in ["week", "month"]:
            # 生成日期序列
            current_date = start_date.date()
            end_date_obj = end_date.date()

            while current_date <= end_date_obj:
                day_start = datetime.combine(current_date, datetime.min.time())
                day_end = datetime.combine(current_date, datetime.max.time())

                count_result = await self.db.execute(
                    select(func.count(NotificationLog.id)).where(
                        and_(
                            NotificationLog.tenant_id == tenant_id,
                            NotificationLog.created_at >= day_start,
                            NotificationLog.created_at <= day_end,
                        )
                    )
                )
                day_count = count_result.scalar() or 0
                daily_trend.append({"date": current_date.isoformat(), "count": day_count})
                current_date += timedelta(days=1)

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "total": total,
            "by_channel": by_channel,
            "by_type": by_type,
            "by_status": by_status,
            "daily_trend": daily_trend,
        }

    async def get_channel_usage_in_period(
        self,
        tenant_id: str,
        channel: str,
        start_date: datetime,
        end_date: datetime,
    ) -> int:
        """获取指定租户在指定时间范围内某渠道的使用量

        Args:
            tenant_id: 租户ID
            channel: 通知渠道
            start_date: 开始时间
            end_date: 结束时间

        Returns:
            发送成功的数量
        """
        result = await self.db.execute(
            select(func.count(NotificationLog.id)).where(
                and_(
                    NotificationLog.tenant_id == tenant_id,
                    NotificationLog.channel == channel,
                    NotificationLog.status == NotificationStatus.SENT.value,
                    NotificationLog.sent_at >= start_date,
                    NotificationLog.sent_at <= end_date,
                )
            )
        )
        return result.scalar() or 0
