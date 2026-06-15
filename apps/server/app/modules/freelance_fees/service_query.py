"""兼职费用 — 查询服务"""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id
from app.models.freelance import (
    FreelanceInteraction,
    Freelancer,
    FreelanceSettlement,
    FreelanceSettlementItem,
    FreelanceTask,
)
from app.modules.freelance_fees.schemas import (
    FreelancerQuery,
    FreelanceSettlementQuery,
    FreelanceTaskQuery,
)


class FreelanceQueryMixin:
    """兼职费用查询"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- 兼职人员 ----------

    async def get_freelancer_by_id(self, freelancer_id: str) -> Freelancer | None:
        stmt = select(Freelancer).where(Freelancer.id == freelancer_id)
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(Freelancer.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_freelancer_list(self, query: FreelancerQuery) -> tuple[list[Freelancer], int]:
        stmt = select(Freelancer)
        count_stmt = select(func.count(Freelancer.id))

        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(Freelancer.tenant_id == tenant_id)
            count_stmt = count_stmt.where(Freelancer.tenant_id == tenant_id)

        if query.store_id:
            stmt = stmt.where(Freelancer.store_id == query.store_id)
            count_stmt = count_stmt.where(Freelancer.store_id == query.store_id)

        if query.name:
            stmt = stmt.where(Freelancer.name.ilike(f"%{query.name}%"))
            count_stmt = count_stmt.where(Freelancer.name.ilike(f"%{query.name}%"))

        if query.status is not None:
            stmt = stmt.where(Freelancer.status == query.status)
            count_stmt = count_stmt.where(Freelancer.status == query.status)

        stmt = stmt.order_by(Freelancer.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)

        result = await self.db.execute(stmt)
        count_result = await self.db.execute(count_stmt)
        return list(result.scalars().all()), count_result.scalar() or 0

    # ---------- 发布任务 ----------

    async def get_task_by_id(self, task_id: str) -> FreelanceTask | None:
        stmt = select(FreelanceTask).where(FreelanceTask.id == task_id)
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(FreelanceTask.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_task_list(self, query: FreelanceTaskQuery) -> tuple[list[FreelanceTask], int]:
        stmt = select(FreelanceTask)
        count_stmt = select(func.count(FreelanceTask.id))

        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(FreelanceTask.tenant_id == tenant_id)
            count_stmt = count_stmt.where(FreelanceTask.tenant_id == tenant_id)

        if query.freelancer_id:
            stmt = stmt.where(FreelanceTask.freelancer_id == query.freelancer_id)
            count_stmt = count_stmt.where(FreelanceTask.freelancer_id == query.freelancer_id)

        if query.store_id:
            stmt = stmt.where(FreelanceTask.store_id == query.store_id)
            count_stmt = count_stmt.where(FreelanceTask.store_id == query.store_id)

        if query.status:
            stmt = stmt.where(FreelanceTask.status == query.status)
            count_stmt = count_stmt.where(FreelanceTask.status == query.status)

        if query.start_date:
            stmt = stmt.where(FreelanceTask.published_at >= query.start_date)
            count_stmt = count_stmt.where(FreelanceTask.published_at >= query.start_date)

        if query.end_date:
            stmt = stmt.where(FreelanceTask.published_at <= query.end_date)
            count_stmt = count_stmt.where(FreelanceTask.published_at <= query.end_date)

        stmt = stmt.order_by(FreelanceTask.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)

        result = await self.db.execute(stmt)
        count_result = await self.db.execute(count_stmt)
        return list(result.scalars().all()), count_result.scalar() or 0

    # ---------- 互动记录 ----------

    async def get_interactions_by_task(self, task_id: str) -> list[FreelanceInteraction]:
        stmt = (
            select(FreelanceInteraction)
            .where(FreelanceInteraction.task_id == task_id)
            .order_by(FreelanceInteraction.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ---------- 结算单 ----------

    async def get_settlement_by_id(self, settlement_id: str) -> FreelanceSettlement | None:
        stmt = (
            select(FreelanceSettlement)
            .where(FreelanceSettlement.id == settlement_id)
        )
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(FreelanceSettlement.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_settlement_list(self, query: FreelanceSettlementQuery) -> tuple[list[FreelanceSettlement], int]:
        stmt = select(FreelanceSettlement)
        count_stmt = select(func.count(FreelanceSettlement.id))

        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(FreelanceSettlement.tenant_id == tenant_id)
            count_stmt = count_stmt.where(FreelanceSettlement.tenant_id == tenant_id)

        if query.freelancer_id:
            stmt = stmt.where(FreelanceSettlement.freelancer_id == query.freelancer_id)
            count_stmt = count_stmt.where(FreelanceSettlement.freelancer_id == query.freelancer_id)

        if query.store_id:
            stmt = stmt.where(FreelanceSettlement.store_id == query.store_id)
            count_stmt = count_stmt.where(FreelanceSettlement.store_id == query.store_id)

        if query.status:
            stmt = stmt.where(FreelanceSettlement.status == query.status)
            count_stmt = count_stmt.where(FreelanceSettlement.status == query.status)

        if query.start_date:
            stmt = stmt.where(FreelanceSettlement.created_at >= query.start_date)
            count_stmt = count_stmt.where(FreelanceSettlement.created_at >= query.start_date)

        if query.end_date:
            stmt = stmt.where(FreelanceSettlement.created_at <= query.end_date)
            count_stmt = count_stmt.where(FreelanceSettlement.created_at <= query.end_date)

        stmt = stmt.order_by(FreelanceSettlement.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)

        result = await self.db.execute(stmt)
        count_result = await self.db.execute(count_stmt)
        return list(result.scalars().all()), count_result.scalar() or 0

    async def get_settlement_items(self, settlement_id: str) -> list[FreelanceSettlementItem]:
        stmt = (
            select(FreelanceSettlementItem)
            .where(FreelanceSettlementItem.settlement_id == settlement_id)
            .order_by(FreelanceSettlementItem.item_type, FreelanceSettlementItem.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ---------- 统计 ----------

    async def get_freelancer_stats(self, store_id: str | None = None) -> dict:
        """兼职人员统计"""
        tenant_id = get_current_tenant_id()

        # 总人数
        count_stmt = select(func.count(Freelancer.id)).where(Freelancer.status == 1)
        if tenant_id:
            count_stmt = count_stmt.where(Freelancer.tenant_id == tenant_id)
        if store_id:
            count_stmt = count_stmt.where(Freelancer.store_id == store_id)
        total_count = (await self.db.execute(count_stmt)).scalar() or 0

        # 总结算金额
        settle_stmt = select(func.sum(FreelanceSettlement.actual_amount)).where(
            FreelanceSettlement.status.in_(["confirmed", "paid"])
        )
        if tenant_id:
            settle_stmt = settle_stmt.where(FreelanceSettlement.tenant_id == tenant_id)
        if store_id:
            settle_stmt = settle_stmt.where(FreelanceSettlement.store_id == store_id)
        total_settled = (await self.db.execute(settle_stmt)).scalar() or 0

        # 待结算金额
        pending_stmt = select(func.sum(FreelanceSettlement.actual_amount)).where(
            FreelanceSettlement.status == "pending"
        )
        if tenant_id:
            pending_stmt = pending_stmt.where(FreelanceSettlement.tenant_id == tenant_id)
        if store_id:
            pending_stmt = pending_stmt.where(FreelanceSettlement.store_id == store_id)
        total_pending = (await self.db.execute(pending_stmt)).scalar() or 0

        return {
            "total_freelancers": total_count,
            "total_settled_amount": float(total_settled),
            "total_pending_amount": float(total_pending),
        }

    async def get_stats_by_freelancer(self, store_id: str | None = None) -> list:
        """按兼职人员汇总"""
        tenant_id = get_current_tenant_id()
        stmt = (
            select(
                FreelanceSettlement.freelancer_id,
                Freelancer.name.label("freelancer_name"),
                func.count(FreelanceSettlement.id).label("settlement_count"),
                func.coalesce(func.sum(FreelanceSettlement.total_amount), 0).label("total_amount"),
                func.coalesce(func.sum(FreelanceSettlement.actual_amount), 0).label("actual_amount"),
            )
            .join(Freelancer, FreelanceSettlement.freelancer_id == Freelancer.id)
            .where(FreelanceSettlement.status.in_(["confirmed", "paid"]))
            .group_by(FreelanceSettlement.freelancer_id, Freelancer.name)
            .order_by(func.sum(FreelanceSettlement.actual_amount).desc())
        )
        if tenant_id:
            stmt = stmt.where(FreelanceSettlement.tenant_id == tenant_id)
        if store_id:
            stmt = stmt.where(FreelanceSettlement.store_id == store_id)

        result = await self.db.execute(stmt)
        return [
            {
                "freelancer_id": row.freelancer_id,
                "freelancer_name": row.freelancer_name,
                "settlement_count": row.settlement_count,
                "total_amount": float(row.total_amount),
                "actual_amount": float(row.actual_amount),
            }
            for row in result.all()
        ]

    async def get_stats_by_month(self, store_id: str | None = None, months: int = 12) -> list:
        """按月汇总（近 N 个月）"""
        from datetime import timedelta

        tenant_id = get_current_tenant_id()
        start_date = datetime.utcnow() - timedelta(days=months * 30)

        stmt = (
            select(
                func.date_trunc("month", FreelanceSettlement.created_at).label("month"),
                func.count(FreelanceSettlement.id).label("settlement_count"),
                func.coalesce(func.sum(FreelanceSettlement.total_amount), 0).label("total_amount"),
                func.coalesce(func.sum(FreelanceSettlement.actual_amount), 0).label("actual_amount"),
            )
            .where(FreelanceSettlement.status.in_(["confirmed", "paid"]))
            .where(FreelanceSettlement.created_at >= start_date)
            .group_by(func.date_trunc("month", FreelanceSettlement.created_at))
            .order_by(func.date_trunc("month", FreelanceSettlement.created_at).desc())
        )
        if tenant_id:
            stmt = stmt.where(FreelanceSettlement.tenant_id == tenant_id)
        if store_id:
            stmt = stmt.where(FreelanceSettlement.store_id == store_id)

        result = await self.db.execute(stmt)
        return [
            {
                "month": row.month.strftime("%Y-%m") if row.month else None,
                "settlement_count": row.settlement_count,
                "total_amount": float(row.total_amount),
                "actual_amount": float(row.actual_amount),
            }
            for row in result.all()
        ]

    async def get_task_stats(self, store_id: str | None = None) -> dict:
        """任务统计"""
        tenant_id = get_current_tenant_id()

        # 各状态任务数
        stmt = (
            select(
                FreelanceTask.status,
                func.count(FreelanceTask.id).label("count"),
            )
            .group_by(FreelanceTask.status)
        )
        if tenant_id:
            stmt = stmt.where(FreelanceTask.tenant_id == tenant_id)
        if store_id:
            stmt = stmt.where(FreelanceTask.store_id == store_id)

        result = await self.db.execute(stmt)
        status_counts = {row.status: row.count for row in result.all()}

        # 总互动数
        interaction_stmt = select(func.count(FreelanceInteraction.id))
        if tenant_id:
            interaction_stmt = interaction_stmt.where(FreelanceInteraction.tenant_id == tenant_id)
        total_interactions = (await self.db.execute(interaction_stmt)).scalar() or 0

        return {
            "task_counts": status_counts,
            "total_tasks": sum(status_counts.values()),
            "total_interactions": total_interactions,
        }
