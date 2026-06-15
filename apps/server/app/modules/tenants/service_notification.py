"""租户通知服务"""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import TenantNotification


class TenantNotificationService:
    """租户通知服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_notifications(
        self,
        tenant_id: str,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TenantNotification], int, int]:
        """获取通知列表，返回 (items, unread_count, total)"""
        base = select(TenantNotification).where(TenantNotification.tenant_id == tenant_id)
        count_base = select(func.count(TenantNotification.id)).where(TenantNotification.tenant_id == tenant_id)

        if unread_only:
            base = base.where(TenantNotification.is_read == False)  # noqa: E712
            count_base = count_base.where(TenantNotification.is_read == False)  # noqa: E712

        # 未读数（始终基于全部）
        unread_result = await self.db.execute(
            select(func.count(TenantNotification.id)).where(
                TenantNotification.tenant_id == tenant_id,
                TenantNotification.is_read == False,  # noqa: E712
            )
        )
        unread_count = unread_result.scalar() or 0

        # 总数
        total_result = await self.db.execute(count_base)
        total = total_result.scalar() or 0

        # 分页
        query = base.order_by(TenantNotification.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, unread_count, total

    async def mark_read(self, tenant_id: str, notification_id: str) -> bool:
        """标记单条已读"""
        result = await self.db.execute(
            select(TenantNotification).where(
                TenantNotification.id == notification_id,
                TenantNotification.tenant_id == tenant_id,
            )
        )
        notification = result.scalar_one_or_none()
        if not notification:
            return False
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        await self.db.commit()
        return True

    async def mark_all_read(self, tenant_id: str) -> int:
        """标记全部已读，返回影响行数"""
        result = await self.db.execute(
            select(TenantNotification).where(
                TenantNotification.tenant_id == tenant_id,
                TenantNotification.is_read == False,  # noqa: E712
            )
        )
        notifications = list(result.scalars().all())
        now = datetime.utcnow()
        for n in notifications:
            n.is_read = True
            n.read_at = now
        await self.db.commit()
        return len(notifications)
