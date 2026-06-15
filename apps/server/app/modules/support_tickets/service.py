import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id
from app.models.support_ticket import SupportTicket, SupportTicketStatus
from app.schemas.support_ticket import (
    SupportTicketCreate,
    SupportTicketQuery,
    SupportTicketUpdate,
)


class SupportTicketService:
    """工单支持服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _tenant_filter(self, stmt):
        """为查询添加租户过滤"""
        tenant_id = get_current_tenant_id()
        if tenant_id:
            return stmt.where(SupportTicket.tenant_id == tenant_id)
        return stmt

    async def get_by_id(self, ticket_id: str) -> SupportTicket | None:
        """根据ID获取工单"""
        stmt = self._tenant_filter(
            select(SupportTicket).where(SupportTicket.id == ticket_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_list(
        self, query: SupportTicketQuery
    ) -> tuple[list[SupportTicket], int]:
        """获取工单列表"""
        stmt = self._tenant_filter(select(SupportTicket))
        count_stmt = self._tenant_filter(select(func.count(SupportTicket.id)))

        if query.status:
            stmt = stmt.where(SupportTicket.status == query.status.value)
            count_stmt = count_stmt.where(SupportTicket.status == query.status.value)

        if query.type:
            stmt = stmt.where(SupportTicket.type == query.type.value)
            count_stmt = count_stmt.where(SupportTicket.type == query.type.value)

        if query.priority:
            stmt = stmt.where(SupportTicket.priority == query.priority.value)
            count_stmt = count_stmt.where(
                SupportTicket.priority == query.priority.value
            )

        if query.keyword:
            keyword_filter = (
                SupportTicket.title.contains(query.keyword)
                | SupportTicket.description.contains(query.keyword)
            )
            stmt = stmt.where(keyword_filter)
            count_stmt = count_stmt.where(keyword_filter)

        stmt = stmt.order_by(SupportTicket.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(
            query.page_size
        )

        result = await self.db.execute(stmt)
        count_result = await self.db.execute(count_stmt)

        return list(result.scalars().all()), count_result.scalar() or 0

    async def create(
        self,
        data: SupportTicketCreate,
        creator_id: str,
        creator_type: str = "user",
    ) -> SupportTicket:
        """创建工单"""
        ticket = SupportTicket(
            id=str(uuid.uuid4()),
            tenant_id=get_current_tenant_id(),
            title=data.title,
            description=data.description,
            type=data.type.value,
            status=SupportTicketStatus.PENDING.value,
            priority=data.priority.value,
            creator_id=creator_id,
            creator_type=creator_type,
            contact_info=data.contact_info,
            attachments=data.attachments,
        )
        self.db.add(ticket)
        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    async def update(
        self, ticket_id: str, data: SupportTicketUpdate
    ) -> SupportTicket | None:
        """更新工单"""
        ticket = await self.get_by_id(ticket_id)
        if not ticket:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field in ("type", "priority", "status") and hasattr(value, "value"):
                value = value.value
            if field == "attachments" and value is not None:
                pass
            setattr(ticket, field, value)

        ticket.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    async def assign(
        self, ticket_id: str, assignee_id: str
    ) -> SupportTicket | None:
        """分配工单"""
        ticket = await self.get_by_id(ticket_id)
        if not ticket:
            return None

        ticket.assignee_id = assignee_id
        if ticket.status == SupportTicketStatus.PENDING.value:
            ticket.status = SupportTicketStatus.PROCESSING.value
        ticket.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    async def resolve(
        self, ticket_id: str, resolution: str | None = None
    ) -> SupportTicket | None:
        """解决工单"""
        ticket = await self.get_by_id(ticket_id)
        if not ticket:
            return None

        ticket.status = SupportTicketStatus.RESOLVED.value
        if resolution is not None:
            ticket.resolution = resolution
        ticket.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    async def close(
        self, ticket_id: str, resolution: str | None = None
    ) -> SupportTicket | None:
        """关闭工单"""
        ticket = await self.get_by_id(ticket_id)
        if not ticket:
            return None

        ticket.status = SupportTicketStatus.CLOSED.value
        if resolution is not None:
            ticket.resolution = resolution
        ticket.closed_at = datetime.utcnow()
        ticket.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    async def reopen(self, ticket_id: str) -> SupportTicket | None:
        """重开工单"""
        ticket = await self.get_by_id(ticket_id)
        if not ticket:
            return None

        ticket.status = SupportTicketStatus.PENDING.value
        ticket.closed_at = None
        ticket.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    async def delete(self, ticket_id: str) -> bool:
        """删除工单"""
        ticket = await self.get_by_id(ticket_id)
        if not ticket:
            return False

        await self.db.delete(ticket)
        await self.db.commit()
        return True

    async def get_statistics(self) -> dict:
        """获取工单统计"""
        tenant_id = get_current_tenant_id()

        # 总数
        total_stmt = select(func.count(SupportTicket.id))
        if tenant_id:
            total_stmt = total_stmt.where(SupportTicket.tenant_id == tenant_id)
        total_result = await self.db.execute(total_stmt)
        total = total_result.scalar() or 0

        # 各状态数量
        status_counts = {}
        for status in [
            SupportTicketStatus.PENDING.value,
            SupportTicketStatus.PROCESSING.value,
            SupportTicketStatus.RESOLVED.value,
            SupportTicketStatus.CLOSED.value,
        ]:
            stmt = select(func.count(SupportTicket.id)).where(
                SupportTicket.status == status
            )
            if tenant_id:
                stmt = stmt.where(SupportTicket.tenant_id == tenant_id)
            result = await self.db.execute(stmt)
            status_counts[status] = result.scalar() or 0

        return {
            "total": total,
            "pending": status_counts.get(SupportTicketStatus.PENDING.value, 0),
            "processing": status_counts.get(
                SupportTicketStatus.PROCESSING.value, 0
            ),
            "resolved": status_counts.get(SupportTicketStatus.RESOLVED.value, 0),
            "closed": status_counts.get(SupportTicketStatus.CLOSED.value, 0),
        }
