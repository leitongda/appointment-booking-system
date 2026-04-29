"""候补队列查询服务"""
from sqlalchemy import select, and_
from typing import Optional, List

from app.models.waitlist import WaitlistEntry
from app.middleware.tenant_context import get_current_tenant_id


class WaitlistQueryMixin:
    """候补队列 - 查询方法"""

    def _tenant_filter(self, stmt):
        """为查询添加租户过滤"""
        tenant_id = get_current_tenant_id()
        if tenant_id:
            return stmt.where(WaitlistEntry.tenant_id == tenant_id)
        return stmt

    async def get_waitlist_position(
        self,
        schedule_id: str,
        user_id: str
    ) -> Optional[int]:
        """获取用户在候补队列中的位置

        Args:
            schedule_id: 排班ID
            user_id: 用户ID

        Returns:
            位置（从1开始），如果不在队列中返回 None
        """
        result = await self.db.execute(
            self._tenant_filter(
                select(WaitlistEntry.position).where(
                    and_(
                        WaitlistEntry.schedule_id == schedule_id,
                        WaitlistEntry.user_id == user_id,
                        WaitlistEntry.status == 'WAITING'
                    )
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_waitlist_for_schedule(
        self,
        schedule_id: str,
        status: str = 'WAITING'
    ) -> List[WaitlistEntry]:
        """获取排班的候补队列

        Args:
            schedule_id: 排班ID
            status: 状态筛选

        Returns:
            候补列表（按位置排序）
        """
        result = await self.db.execute(
            self._tenant_filter(
                select(WaitlistEntry).where(
                    and_(
                        WaitlistEntry.schedule_id == schedule_id,
                        WaitlistEntry.status == status
                    )
                ).order_by(WaitlistEntry.position)
            )
        )
        return list(result.scalars().all())
