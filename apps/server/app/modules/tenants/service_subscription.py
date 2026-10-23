"""租户订阅服务"""
from datetime import date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.appointment import Appointment
from app.models.tenant import SubscriptionPlan, Tenant, TenantSubscription
from app.modules.tenants.schemas import TenantSubscriptionCreate


class TenantSubscriptionService:
    """租户订阅服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _check_downgrade_quota(
        self,
        tenant_id: str,
        old_plan: SubscriptionPlan,
        new_plan: SubscriptionPlan,
    ) -> None:
        """降级配额检查：当新计划某项配额低于旧计划时，校验当前实际使用量。

        如果任一资源超出新计划配额，抛出 HTTPException 并附上详细信息。
        """
        from app.modules.tenants.service_tenant import TenantService

        tenant_svc = TenantService(self.db)

        quota_dimensions = [
            (
                "max_stores",
                "门店",
                old_plan.max_stores,
                new_plan.max_stores,
                tenant_svc.get_store_count(tenant_id),
            ),
            (
                "max_admins",
                "管理员",
                old_plan.max_admins,
                new_plan.max_admins,
                tenant_svc.get_admin_count(tenant_id),
            ),
            (
                "max_doctors",
                "医生",
                old_plan.max_doctors,
                new_plan.max_doctors,
                tenant_svc.get_doctor_count(tenant_id),
            ),
            (
                "max_appointments_per_month",
                "月预约",
                old_plan.max_appointments_per_month,
                new_plan.max_appointments_per_month,
                self._get_month_appointment_count(tenant_id),
            ),
            (
                "max_lowcode_pages",
                "低代码页面",
                old_plan.max_lowcode_pages,
                new_plan.max_lowcode_pages,
                tenant_svc.get_lowcode_page_count(tenant_id),
            ),
            (
                "max_miniapp_instances",
                "小程序实例",
                old_plan.max_miniapp_instances,
                new_plan.max_miniapp_instances,
                tenant_svc.get_miniapp_instance_count(tenant_id),
            ),
        ]

        violations: list[str] = []
        for field_name, display_name, old_limit, new_limit, coro in quota_dimensions:
            # 只在降级场景检查：新配额严格小于旧配额
            if new_limit >= old_limit:
                continue
            current_usage = await coro
            if current_usage > new_limit:
                violations.append(
                    f"{display_name}：当前 {current_usage}，新计划上限 {new_limit}，超出 {current_usage - new_limit}"
                )

        if violations:
            detail = "降级失败，以下资源超出新计划配额：" + "；".join(violations)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            )

    async def _get_month_appointment_count(self, tenant_id: str) -> int:
        """获取租户本月预约数"""
        today = date.today()
        month_start = today.replace(day=1)

        result = await self.db.execute(
            select(func.count(Appointment.id)).where(
                and_(
                    Appointment.tenant_id == tenant_id,
                    Appointment.created_at >= month_start,
                )
            )
        )
        return result.scalar() or 0

    async def create_subscription(
        self,
        tenant_id: str,
        data: TenantSubscriptionCreate,
        created_by: str | None = None
    ) -> TenantSubscription:
        """创建租户订阅"""
        # 获取租户（加载关联的 subscription_plan）
        result = await self.db.execute(
            select(Tenant)
            .options(selectinload(Tenant.subscription_plan))
            .where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise ValueError("租户不存在")

        # 获取新计划
        new_plan = await self.db.get(SubscriptionPlan, data.plan_id)
        if not new_plan:
            raise ValueError("订阅计划不存在")

        # 降级配额检查：如果租户当前已有订阅计划，且新计划配额更低，则校验实际使用量
        old_plan = tenant.subscription_plan
        if old_plan is not None and old_plan.id != new_plan.id:
            await self._check_downgrade_quota(tenant_id, old_plan, new_plan)

        # 记录旧的订阅信息用于审计
        old_plan_id = old_plan.id if old_plan else None
        old_end_at = str(tenant.subscription_end_at) if tenant.subscription_end_at else None

        # 计算时间范围
        start_at = data.start_at or datetime.utcnow()
        if data.billing_cycle == "yearly":
            end_at = start_at + timedelta(days=365)
            amount = new_plan.price_yearly
        else:
            end_at = start_at + timedelta(days=30)
            amount = new_plan.price_monthly

        # 创建订阅记录
        subscription = TenantSubscription(
            tenant_id=tenant_id,
            plan_id=new_plan.id,
            plan_code=new_plan.plan_code,
            plan_name=new_plan.name,
            billing_cycle=data.billing_cycle,
            start_at=start_at,
            end_at=end_at,
            amount=amount,
            final_amount=amount,
            auto_renew=data.auto_renew,
            created_by=created_by,
        )

        self.db.add(subscription)

        # 更新租户的订阅信息
        tenant.subscription_plan_id = new_plan.id
        tenant.subscription_start_at = start_at
        tenant.subscription_end_at = end_at
        tenant.billing_cycle = data.billing_cycle
        if tenant.status == 2:  # 如果是欠费状态，激活
            tenant.status = 1

        # 审计追踪：订阅变更
        from app.modules.tenants.audit_tracker import AuditTracker
        tracker = AuditTracker(self.db)
        await tracker.track_subscription_change(
            tenant_id=tenant_id,
            old_plan_id=old_plan_id,
            new_plan_id=new_plan.id,
            old_end_at=old_end_at,
            new_end_at=str(end_at),
            actor_id=created_by,
        )

        await self.db.commit()
        await self.db.refresh(subscription)

        return subscription

    async def mark_subscription_paid(
        self,
        tenant_id: str,
        subscription_id: str,
        payment_method: str | None = None,
        transaction_id: str | None = None,
        actor_id: str | None = None,
    ) -> TenantSubscription | None:
        """标记订阅已支付（平台管理员手工回写，P4-5）"""
        subscription = await self.db.get(TenantSubscription, subscription_id)
        if not subscription or subscription.tenant_id != tenant_id:
            return None

        subscription.payment_status = "paid"
        subscription.paid_at = datetime.utcnow()
        if payment_method:
            subscription.payment_method = payment_method
        if transaction_id:
            subscription.payment_transaction_id = transaction_id

        from app.modules.tenants.audit_tracker import AuditTracker

        try:
            await AuditTracker(self.db).track_subscription_change(
                tenant_id=tenant_id,
                old_plan_id=subscription.plan_id,
                new_plan_id=subscription.plan_id,
                old_end_at=str(subscription.end_at),
                new_end_at=str(subscription.end_at),
                actor_id=actor_id,
            )
        except Exception:
            pass

        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription

    async def get_tenant_subscriptions(
        self,
        tenant_id: str,
        limit: int = 10
    ) -> list[TenantSubscription]:
        """获取租户的订阅记录"""
        result = await self.db.execute(
            select(TenantSubscription)
            .where(TenantSubscription.tenant_id == tenant_id)
            .order_by(TenantSubscription.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
