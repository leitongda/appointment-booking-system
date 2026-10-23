"""配额检查工具

提供租户配额实时检查功能，确保创建资源时不超出订阅限制。
"""
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.middleware.tenant_context import get_current_tenant_id
from app.models.tenant import Tenant


class QuotaCheckError(HTTPException):
    """配额检查错误"""
    def __init__(self, message: str, quota_type: str, current: int, limit: int):
        self.quota_type = quota_type
        self.current = current
        self.limit = limit
        detail = f"{message}（当前：{current}，上限：{limit}）"
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class QuotaChecker:
    """配额检查器

    用法:
        checker = QuotaChecker(db)
        await checker.check_stores_quota(tenant_id)
        await checker.check_admins_quota(tenant_id)
        await checker.check_doctors_quota(tenant_id)
        await checker.check_appointments_quota(tenant_id)
    """

    def __init__(self, db):
        self.db = db

    async def _get_tenant(self, tenant_id: str | None = None) -> Tenant | None:
        """获取租户对象（预加载 subscription_plan 避免懒加载）"""
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if not effective_tenant_id:
            return None
        result = await self.db.execute(
            select(Tenant)
            .options(selectinload(Tenant.subscription_plan))
            .where(Tenant.id == effective_tenant_id)
        )
        return result.scalar_one_or_none()

    async def check_stores_quota(self, tenant_id: str | None = None) -> None:
        """检查门店配额

        Args:
            tenant_id: 租户ID，不传则从上下文获取

        Raises:
            QuotaCheckError: 门店数量已达上限
        """
        tenant = await self._get_tenant(tenant_id)
        if not tenant:
            return

        max_stores = tenant.get_effective_max_stores()

        # 统计当前门店数量
        from app.models.store import Store
        result = await self.db.execute(
            select(func.count(Store.id)).where(Store.tenant_id == tenant.id)
        )
        current_count = result.scalar() or 0

        if current_count >= max_stores:
            raise QuotaCheckError(
                message="门店数量已达上限",
                quota_type="stores",
                current=current_count,
                limit=max_stores
            )

    async def check_admins_quota(self, tenant_id: str | None = None) -> None:
        """检查管理员配额

        Args:
            tenant_id: 租户ID，不传则从上下文获取

        Raises:
            QuotaCheckError: 管理员数量已达上限
        """
        tenant = await self._get_tenant(tenant_id)
        if not tenant:
            return

        max_admins = tenant.get_effective_max_admins()

        # 统计当前管理员数量
        from app.models.admin import Admin
        result = await self.db.execute(
            select(func.count(Admin.id)).where(Admin.tenant_id == tenant.id)
        )
        current_count = result.scalar() or 0

        if current_count >= max_admins:
            raise QuotaCheckError(
                message="管理员数量已达上限",
                quota_type="admins",
                current=current_count,
                limit=max_admins
            )

    async def check_doctors_quota(self, tenant_id: str | None = None) -> None:
        """检查医生配额

        Args:
            tenant_id: 租户ID，不传则从上下文获取

        Raises:
            QuotaCheckError: 医生数量已达上限
        """
        tenant = await self._get_tenant(tenant_id)
        if not tenant:
            return

        max_doctors = tenant.get_effective_max_doctors()

        # 统计当前医生数量
        from app.models.doctor import Doctor
        result = await self.db.execute(
            select(func.count(Doctor.id)).where(Doctor.tenant_id == tenant.id, Doctor.deleted_at.is_(None))
        )
        current_count = result.scalar() or 0

        if current_count >= max_doctors:
            raise QuotaCheckError(
                message="医生数量已达上限",
                quota_type="doctors",
                current=current_count,
                limit=max_doctors
            )

    async def check_appointments_quota(self, tenant_id: str | None = None) -> None:
        """检查月预约配额

        Args:
            tenant_id: 租户ID，不传则从上下文获取

        Raises:
            QuotaCheckError: 月预约数量已达上限
        """
        tenant = await self._get_tenant(tenant_id)
        if not tenant:
            return

        max_appointments = tenant.get_effective_max_appointments()

        # 统计本月预约数量
        from app.models.appointment import Appointment

        # 获取当前月份的开始和结束时间
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # 计算下个月第一天
        if now.month == 12:
            month_end = now.replace(year=now.year + 1, month=1, day=1)
        else:
            month_end = now.replace(month=now.month + 1, day=1)

        result = await self.db.execute(
            select(func.count(Appointment.id)).where(
                Appointment.tenant_id == tenant.id,
                Appointment.created_at >= month_start,
                Appointment.created_at < month_end
            )
        )
        current_count = result.scalar() or 0

        if current_count >= max_appointments:
            raise QuotaCheckError(
                message="本月预约数量已达上限",
                quota_type="appointments_per_month",
                current=current_count,
                limit=max_appointments
            )

    async def get_quota_usage(self, tenant_id: str | None = None) -> dict:
        """获取配额使用情况

        Args:
            tenant_id: 租户ID，不传则从上下文获取

        Returns:
            包含各配额使用情况的字典
        """
        tenant = await self._get_tenant(tenant_id)
        if not tenant:
            return {}

        from app.models.admin import Admin
        from app.models.appointment import Appointment
        from app.models.doctor import Doctor
        from app.models.store import Store

        # 统计各资源数量
        stores_count = await self.db.scalar(
            select(func.count(Store.id)).where(Store.tenant_id == tenant.id)
        ) or 0

        admins_count = await self.db.scalar(
            select(func.count(Admin.id)).where(Admin.tenant_id == tenant.id)
        ) or 0

        doctors_count = await self.db.scalar(
            select(func.count(Doctor.id)).where(Doctor.tenant_id == tenant.id, Doctor.deleted_at.is_(None))
        ) or 0

        # 统计本月预约数量
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            month_end = now.replace(year=now.year + 1, month=1, day=1)
        else:
            month_end = now.replace(month=now.month + 1, day=1)

        appointments_count = await self.db.scalar(
            select(func.count(Appointment.id)).where(
                Appointment.tenant_id == tenant.id,
                Appointment.created_at >= month_start,
                Appointment.created_at < month_end
            )
        ) or 0

        return {
            "stores": {
                "current": stores_count,
                "limit": tenant.get_effective_max_stores(),
                "usage_percent": round(stores_count / tenant.get_effective_max_stores() * 100, 2)
                if tenant.get_effective_max_stores() > 0 else 0
            },
            "admins": {
                "current": admins_count,
                "limit": tenant.get_effective_max_admins(),
                "usage_percent": round(admins_count / tenant.get_effective_max_admins() * 100, 2)
                if tenant.get_effective_max_admins() > 0 else 0
            },
            "doctors": {
                "current": doctors_count,
                "limit": tenant.get_effective_max_doctors(),
                "usage_percent": round(doctors_count / tenant.get_effective_max_doctors() * 100, 2)
                if tenant.get_effective_max_doctors() > 0 else 0
            },
            "appointments_per_month": {
                "current": appointments_count,
                "limit": tenant.get_effective_max_appointments(),
                "usage_percent": round(appointments_count / tenant.get_effective_max_appointments() * 100, 2)
                if tenant.get_effective_max_appointments() > 0 else 0
            }
        }


    async def check_miniapp_instances_quota(self, tenant_id: str | None = None) -> None:
        """检查小程序实例配额（P4-6，复用 TenantService 计数）"""
        tenant = await self._get_tenant(tenant_id)
        if not tenant:
            return

        limit = tenant.get_effective_max_miniapp_instances()
        from app.modules.tenants.service_tenant import TenantService

        current_count = await TenantService(self.db).get_miniapp_instance_count(tenant.id)

        if limit and current_count >= limit:
            raise QuotaCheckError(
                message="小程序实例数量已达上限",
                quota_type="miniapp_instances",
                current=current_count,
                limit=limit,
            )

    async def check_lowcode_pages_quota(self, tenant_id: str | None = None) -> None:
        """检查低代码页面配额（P4-6，复用 TenantService 计数）"""
        tenant = await self._get_tenant(tenant_id)
        if not tenant:
            return

        limit = tenant.get_effective_max_lowcode_pages()
        from app.modules.tenants.service_tenant import TenantService

        current_count = await TenantService(self.db).get_lowcode_page_count(tenant.id)

        if limit and current_count >= limit:
            raise QuotaCheckError(
                message="低代码页面数量已达上限",
                quota_type="lowcode_pages",
                current=current_count,
                limit=limit,
            )

    async def check_storage_quota(self, tenant_id: str | None = None) -> None:
        """检查存储配额（P4-6）

        计量数据缺失时放行（当前 storage_used_mb 无写入方），避免误杀。
        """
        tenant = await self._get_tenant(tenant_id)
        if not tenant or not tenant.subscription_plan:
            return

        max_mb = tenant.subscription_plan.max_storage_mb
        if not max_mb:
            return

        from app.modules.tenants.service_usage import TenantUsageService

        summary = await TenantUsageService(self.db).get_usage_summary(tenant.id)
        used_mb = float(summary.get("current_storage_mb") or 0)
        if used_mb <= 0:
            return  # 无用量数据：放行

        if used_mb >= float(max_mb):
            raise QuotaCheckError(
                message="存储空间已达上限",
                quota_type="storage_mb",
                current=used_mb,
                limit=float(max_mb),
            )


async def check_quota(tenant_id: str | None, resource_type: str, db) -> None:
    """通用配额检查函数

    Args:
        tenant_id: 租户ID
        resource_type: 资源类型（stores/admins/doctors/appointments）
        db: 数据库会话

    Raises:
        QuotaCheckError: 配额已达上限
        ValueError: 不支持的资源类型

    用法:
        from app.common.quota import check_quota

        await check_quota(tenant_id, "stores", db)
        await check_quota(tenant_id, "admins", db)
        await check_quota(tenant_id, "doctors", db)
        await check_quota(tenant_id, "appointments", db)
    """
    checker = QuotaChecker(db)

    check_methods = {
        "stores": checker.check_stores_quota,
        "admins": checker.check_admins_quota,
        "doctors": checker.check_doctors_quota,
        "appointments": checker.check_appointments_quota,
        "miniapp_instances": checker.check_miniapp_instances_quota,
        "lowcode_pages": checker.check_lowcode_pages_quota,
        "storage_mb": checker.check_storage_quota,
    }

    check_func = check_methods.get(resource_type)
    if not check_func:
        raise ValueError(f"不支持的资源类型: {resource_type}，支持的类型: {list(check_methods.keys())}")

    await check_func(tenant_id)
