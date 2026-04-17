"""租户管理服务"""
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, Tuple, List
from datetime import datetime, date, timedelta
from decimal import Decimal
import uuid

from app.core.config import settings
from app.models.tenant import Tenant, TenantSubscription, TenantUsageLog, SubscriptionPlan
from app.models.store import Store
from app.models.admin import Admin
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.modules.tenants.schemas import (
    TenantCreate, TenantUpdate, TenantQuery,
    SubscriptionPlanCreate, SubscriptionPlanUpdate,
    TenantSubscriptionCreate
)


class SubscriptionPlanService:
    """订阅计划服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, plan_id: str) -> Optional[SubscriptionPlan]:
        """获取订阅计划"""
        result = await self.db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, plan_code: str) -> Optional[SubscriptionPlan]:
        """通过编码获取订阅计划"""
        result = await self.db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.plan_code == plan_code)
        )
        return result.scalar_one_or_none()

    async def get_list(self, status: Optional[int] = None) -> List[SubscriptionPlan]:
        """获取订阅计划列表"""
        query = select(SubscriptionPlan).order_by(SubscriptionPlan.sort_order, SubscriptionPlan.created_at)
        if status is not None:
            query = query.where(SubscriptionPlan.status == status)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_default_plan(self) -> Optional[SubscriptionPlan]:
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

    async def update(self, plan_id: str, data: SubscriptionPlanUpdate) -> Optional[SubscriptionPlan]:
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


class TenantService:
    """租户服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        """获取租户"""
        result = await self.db.execute(
            select(Tenant)
            .options(selectinload(Tenant.subscription_plan))
            .where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, tenant_code: str) -> Optional[Tenant]:
        """通过编码获取租户"""
        result = await self.db.execute(
            select(Tenant)
            .options(selectinload(Tenant.subscription_plan))
            .where(Tenant.tenant_code == tenant_code)
        )
        return result.scalar_one_or_none()

    async def get_list(self, query: TenantQuery, include_deleted: bool = False) -> Tuple[List[Tenant], int]:
        """获取租户列表

        Args:
            query: 查询条件
            include_deleted: 是否包含已软删除的租户

        Returns:
            (租户列表, 总数)
        """
        base_query = select(Tenant).options(selectinload(Tenant.subscription_plan))

        # 默认过滤已软删除的租户
        if not include_deleted:
            base_query = base_query.where(Tenant.deleted_at.is_(None))

        # 条件过滤
        conditions = []
        if query.keyword:
            keyword = f"%{query.keyword}%"
            conditions.append(
                or_(
                    Tenant.name.ilike(keyword),
                    Tenant.tenant_code.ilike(keyword),
                    Tenant.contact_name.ilike(keyword),
                    Tenant.contact_phone.ilike(keyword),
                )
            )
        if query.status is not None:
            conditions.append(Tenant.status == query.status)
        if query.subscription_plan_id:
            conditions.append(Tenant.subscription_plan_id == query.subscription_plan_id)

        if conditions:
            base_query = base_query.where(and_(*conditions))

        # 统计总数
        count_query = select(func.count(Tenant.id))
        if not include_deleted:
            count_query = count_query.where(Tenant.deleted_at.is_(None))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # 分页
        offset = (query.page - 1) * query.page_size
        base_query = base_query.order_by(Tenant.created_at.desc()).offset(offset).limit(query.page_size)

        result = await self.db.execute(base_query)
        tenants = list(result.scalars().all())

        return tenants, total

    async def create(self, data: TenantCreate, created_by: Optional[str] = None) -> Tenant:
        """创建租户"""
        # 检查编码是否已存在
        existing = await self.get_by_code(data.tenant_code)
        if existing:
            raise ValueError(f"租户标识 '{data.tenant_code}' 已存在")

        # 获取订阅计划
        plan = None
        if data.subscription_plan_id:
            plan = await self.db.get(SubscriptionPlan, data.subscription_plan_id)
            if not plan:
                raise ValueError("订阅计划不存在")

        # 计算订阅时间
        now = datetime.utcnow()
        if data.billing_cycle == "yearly":
            end_at = now + timedelta(days=365)
        else:
            end_at = now + timedelta(days=30)

        tenant = Tenant(
            tenant_code=data.tenant_code,
            name=data.name,
            status=3 if data.is_trial else 1,  # 试用租户状态为3
            subscription_plan_id=data.subscription_plan_id,
            subscription_start_at=now,
            subscription_end_at=end_at,
            billing_cycle=data.billing_cycle,
            max_stores=data.max_stores,
            max_admins=data.max_admins,
            max_doctors=data.max_doctors,
            max_appointments_per_month=data.max_appointments_per_month,
            features=data.features,
            branding_config=data.branding_config,
            contact_name=data.contact_name,
            contact_phone=data.contact_phone,
            contact_email=data.contact_email,
            address=data.address,
            custom_domain=data.custom_domain,
            subdomain=data.subdomain,
            created_by=created_by,
        )

        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)

        # 重新加载关联
        await self.db.refresh(tenant, ["subscription_plan"])

        return tenant

    async def update(self, tenant_id: str, data: TenantUpdate, updated_by: Optional[str] = None) -> Optional[Tenant]:
        """更新租户"""
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(tenant, key, value)

        tenant.updated_by = updated_by
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def update_status(self, tenant_id: str, new_status: int) -> Optional[Tenant]:
        """更新租户状态"""
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return None

        tenant.status = new_status
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def suspend(self, tenant_id: str) -> Optional[Tenant]:
        """暂停租户"""
        return await self.update_status(tenant_id, 0)

    async def activate(self, tenant_id: str) -> Optional[Tenant]:
        """激活租户"""
        return await self.update_status(tenant_id, 1)

    async def mark_overdue(self, tenant_id: str) -> Optional[Tenant]:
        """标记租户为欠费"""
        return await self.update_status(tenant_id, 2)

    async def delete(self, tenant_id: str, deleted_by: Optional[str] = None) -> bool:
        """删除租户（软删除）

        软删除策略：
        - 设置 deleted_at 和 deleted_by 字段
        - 设置 status 为 0（禁用）
        - 保留所有关联数据 90 天后才能物理删除
        - 删除后租户无法登录和访问

        Args:
            tenant_id: 租户ID
            deleted_by: 操作人ID

        Returns:
            是否删除成功
        """
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return False

        # 检查是否已经软删除
        if tenant.deleted_at is not None:
            raise ValueError("租户已被删除")

        # 软删除
        tenant.deleted_at = datetime.utcnow()
        tenant.deleted_by = deleted_by
        tenant.status = 0  # 禁用
        await self.db.commit()
        return True

    async def restore(self, tenant_id: str, restored_by: Optional[str] = None) -> Optional[Tenant]:
        """恢复已软删除的租户

        Args:
            tenant_id: 租户ID
            restored_by: 操作人ID

        Returns:
            恢复的租户对象
        """
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            return None

        # 检查是否已软删除
        if tenant.deleted_at is None:
            raise ValueError("租户未被删除，无需恢复")

        # 恢复
        tenant.deleted_at = None
        tenant.deleted_by = None
        tenant.status = 1  # 正常
        tenant.updated_by = restored_by
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def get_store_count(self, tenant_id: str) -> int:
        """获取租户的门店数量"""
        result = await self.db.execute(
            select(func.count(Store.id)).where(Store.tenant_id == tenant_id)
        )
        return result.scalar() or 0

    async def get_admin_count(self, tenant_id: str) -> int:
        """获取租户的管理员数量"""
        result = await self.db.execute(
            select(func.count(Admin.id)).where(Admin.tenant_id == tenant_id)
        )
        return result.scalar() or 0

    async def get_store_counts_batch(self, tenant_ids: List[str]) -> dict:
        """批量获取租户的门店数量

        Args:
            tenant_ids: 租户ID列表

        Returns:
            {tenant_id: count} 的字典
        """
        if not tenant_ids:
            return {}

        result = await self.db.execute(
            select(Store.tenant_id, func.count(Store.id).label("count"))
            .where(Store.tenant_id.in_(tenant_ids))
            .group_by(Store.tenant_id)
        )
        return {row.tenant_id: row.count for row in result.all()}

    async def get_admin_counts_batch(self, tenant_ids: List[str]) -> dict:
        """批量获取租户的管理员数量

        Args:
            tenant_ids: 租户ID列表

        Returns:
            {tenant_id: count} 的字典
        """
        if not tenant_ids:
            return {}

        result = await self.db.execute(
            select(Admin.tenant_id, func.count(Admin.id).label("count"))
            .where(Admin.tenant_id.in_(tenant_ids))
            .group_by(Admin.tenant_id)
        )
        return {row.tenant_id: row.count for row in result.all()}

    async def get_doctor_count(self, tenant_id: str) -> int:
        """获取租户的医生数量"""
        # 通过门店关联获取医生数
        result = await self.db.execute(
            select(func.count(Doctor.id))
            .join(Store, Doctor.store_id == Store.id)
            .where(Store.tenant_id == tenant_id)
        )
        return result.scalar() or 0

    async def check_code_exists(self, tenant_code: str, exclude_id: Optional[str] = None) -> bool:
        """检查租户编码是否已存在"""
        query = select(func.count(Tenant.id)).where(Tenant.tenant_code == tenant_code)
        if exclude_id:
            query = query.where(Tenant.id != exclude_id)
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0


class TenantSubscriptionService:
    """租户订阅服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_subscription(
        self,
        tenant_id: str,
        data: TenantSubscriptionCreate,
        created_by: Optional[str] = None
    ) -> TenantSubscription:
        """创建租户订阅"""
        # 获取租户
        tenant = await self.db.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError("租户不存在")

        # 获取计划
        plan = await self.db.get(SubscriptionPlan, data.plan_id)
        if not plan:
            raise ValueError("订阅计划不存在")

        # 计算时间范围
        start_at = data.start_at or datetime.utcnow()
        if data.billing_cycle == "yearly":
            end_at = start_at + timedelta(days=365)
            amount = plan.price_yearly
        else:
            end_at = start_at + timedelta(days=30)
            amount = plan.price_monthly

        # 创建订阅记录
        subscription = TenantSubscription(
            tenant_id=tenant_id,
            plan_id=plan.id,
            plan_code=plan.plan_code,
            plan_name=plan.name,
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
        tenant.subscription_plan_id = plan.id
        tenant.subscription_start_at = start_at
        tenant.subscription_end_at = end_at
        tenant.billing_cycle = data.billing_cycle
        if tenant.status == 2:  # 如果是欠费状态，激活
            tenant.status = 1

        await self.db.commit()
        await self.db.refresh(subscription)

        return subscription

    async def get_tenant_subscriptions(
        self,
        tenant_id: str,
        limit: int = 10
    ) -> List[TenantSubscription]:
        """获取租户的订阅记录"""
        result = await self.db.execute(
            select(TenantSubscription)
            .where(TenantSubscription.tenant_id == tenant_id)
            .order_by(TenantSubscription.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class TenantUsageService:
    """租户用量统计服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_usage_summary(self, tenant_id: str) -> dict:
        """获取租户用量汇总"""
        stmt = select(Tenant).where(Tenant.id == tenant_id).options(selectinload(Tenant.subscription_plan))
        result = await self.db.execute(stmt)
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise ValueError("租户不存在")

        # 获取配额
        max_stores = tenant.get_effective_max_stores()
        max_admins = tenant.get_effective_max_admins()
        max_doctors = tenant.get_effective_max_doctors()
        max_appointments = tenant.get_effective_max_appointments()

        # 获取当前使用量
        store_count = await self._get_store_count(tenant_id)
        admin_count = await self._get_admin_count(tenant_id)
        doctor_count = await self._get_doctor_count(tenant_id)
        month_appointments = await self._get_month_appointment_count(tenant_id)
        storage_mb = await self._get_storage_usage(tenant_id)

        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant.name,
            "max_stores": max_stores,
            "max_admins": max_admins,
            "max_doctors": max_doctors,
            "max_appointments_per_month": max_appointments,
            "current_store_count": store_count,
            "current_admin_count": admin_count,
            "current_doctor_count": doctor_count,
            "current_month_appointments": month_appointments,
            "current_storage_mb": storage_mb,
            "store_usage_rate": round(store_count / max_stores * 100, 2) if max_stores > 0 else 0,
            "admin_usage_rate": round(admin_count / max_admins * 100, 2) if max_admins > 0 else 0,
            "doctor_usage_rate": round(doctor_count / max_doctors * 100, 2) if max_doctors > 0 else 0,
            "appointment_usage_rate": round(month_appointments / max_appointments * 100, 2) if max_appointments > 0 else 0,
        }

    async def get_usage_logs(
        self,
        tenant_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 30
    ) -> List[TenantUsageLog]:
        """获取租户用量日志"""
        query = select(TenantUsageLog).where(TenantUsageLog.tenant_id == tenant_id)

        if start_date:
            query = query.where(TenantUsageLog.usage_date >= start_date)
        if end_date:
            query = query.where(TenantUsageLog.usage_date <= end_date)

        query = query.order_by(TenantUsageLog.usage_date.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def record_daily_usage(self, tenant_id: str, usage_date: Optional[date] = None) -> TenantUsageLog:
        """记录每日用量（定时任务调用）"""
        usage_date = usage_date or date.today()

        # 检查是否已存在
        result = await self.db.execute(
            select(TenantUsageLog).where(
                and_(
                    TenantUsageLog.tenant_id == tenant_id,
                    TenantUsageLog.usage_date == usage_date
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # 更新现有记录
            log = existing
        else:
            # 创建新记录
            log = TenantUsageLog(
                tenant_id=tenant_id,
                usage_date=usage_date
            )
            self.db.add(log)

        # 统计数据
        log.appointment_count = await self._get_day_appointment_count(tenant_id, usage_date)
        log.new_user_count = await self._get_day_new_user_count(tenant_id, usage_date)
        log.active_doctor_count = await self._get_doctor_count(tenant_id)

        await self.db.commit()
        await self.db.refresh(log)

        return log

    async def _get_store_count(self, tenant_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Store.id)).where(Store.tenant_id == tenant_id)
        )
        return result.scalar() or 0

    async def _get_admin_count(self, tenant_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Admin.id)).where(Admin.tenant_id == tenant_id)
        )
        return result.scalar() or 0

    async def _get_doctor_count(self, tenant_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Doctor.id))
            .join(Store, Doctor.store_id == Store.id)
            .where(Store.tenant_id == tenant_id)
        )
        return result.scalar() or 0

    async def _get_month_appointment_count(self, tenant_id: str) -> int:
        """获取本月预约数"""
        today = date.today()
        month_start = today.replace(day=1)

        result = await self.db.execute(
            select(func.count(Appointment.id))
            .where(
                and_(
                    Appointment.tenant_id == tenant_id,
                    Appointment.created_at >= month_start
                )
            )
        )
        return result.scalar() or 0

    async def _get_day_appointment_count(self, tenant_id: str, usage_date: date) -> int:
        """获取当日预约数"""
        day_start = datetime.combine(usage_date, datetime.min.time())
        day_end = datetime.combine(usage_date, datetime.max.time())

        result = await self.db.execute(
            select(func.count(Appointment.id))
            .where(
                and_(
                    Appointment.tenant_id == tenant_id,
                    Appointment.created_at >= day_start,
                    Appointment.created_at <= day_end
                )
            )
        )
        return result.scalar() or 0

    async def _get_day_new_user_count(self, tenant_id: str, usage_date: date) -> int:
        """获取当日新用户数"""
        from app.models.user import User, Patient

        day_start = datetime.combine(usage_date, datetime.min.time())
        day_end = datetime.combine(usage_date, datetime.max.time())

        # 通过患者首次就诊门店统计
        result = await self.db.execute(
            select(func.count(Patient.id))
            .join(Store, Patient.first_visit_store_id == Store.id)
            .where(
                and_(
                    Store.tenant_id == tenant_id,
                    Patient.created_at >= day_start,
                    Patient.created_at <= day_end
                )
            )
        )
        return result.scalar() or 0

    async def _get_storage_usage(self, tenant_id: str) -> Decimal:
        """获取存储使用量（MB）"""
        if settings.STORAGE_TYPE.lower() != "local":
            return Decimal("0")

        tenant_upload_dir = Path(settings.LOCAL_UPLOAD_DIR) / "tenants" / tenant_id
        if not tenant_upload_dir.exists():
            return Decimal("0")

        total_bytes = 0
        for path in tenant_upload_dir.rglob("*"):
            if path.is_file():
                total_bytes += path.stat().st_size

        megabyte = Decimal(1024 * 1024)
        return (Decimal(total_bytes) / megabyte).quantize(Decimal("0.0001"))
