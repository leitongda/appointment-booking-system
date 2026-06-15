"""订阅计划服务"""

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import SubscriptionPlan, Tenant
from app.modules.tenants.schemas import (
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
)


class SubscriptionPlanService:
    """订阅计划服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, plan_id: str) -> SubscriptionPlan | None:
        """获取订阅计划"""
        result = await self.db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, plan_code: str) -> SubscriptionPlan | None:
        """通过编码获取订阅计划"""
        result = await self.db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.plan_code == plan_code)
        )
        return result.scalar_one_or_none()

    async def get_list(self, status: int | None = None) -> list[SubscriptionPlan]:
        """获取订阅计划列表"""
        query = select(SubscriptionPlan).order_by(SubscriptionPlan.sort_order, SubscriptionPlan.created_at)
        if status is not None:
            query = query.where(SubscriptionPlan.status == status)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_default_plan(self) -> SubscriptionPlan | None:
        """获取默认订阅计划"""
        result = await self.db.execute(
            select(SubscriptionPlan).where(
                and_(
                    SubscriptionPlan.is_default == True,
                    SubscriptionPlan.status == 1
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, data: SubscriptionPlanCreate) -> SubscriptionPlan:
        """创建订阅计划"""
        # 检查编码是否已存在
        existing = await self.get_by_code(data.plan_code)
        if existing:
            raise ValueError(f"计划编码 '{data.plan_code}' 已存在")

        plan = SubscriptionPlan(**data.model_dump())
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def update(self, plan_id: str, data: SubscriptionPlanUpdate) -> SubscriptionPlan | None:
        """更新订阅计划"""
        plan = await self.get_by_id(plan_id)
        if not plan:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(plan, key, value)

        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def delete(self, plan_id: str) -> bool:
        """删除订阅计划"""
        plan = await self.get_by_id(plan_id)
        if not plan:
            return False

        # 检查是否有租户使用此计划
        result = await self.db.execute(
            select(func.count(Tenant.id)).where(Tenant.subscription_plan_id == plan_id)
        )
        count = result.scalar()
        if count > 0:
            raise ValueError(f"有 {count} 个租户正在使用此计划，无法删除")

        await self.db.delete(plan)
        await self.db.commit()
        return True
