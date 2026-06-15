"""租户用量统计服务"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.admin import Admin
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.store import Store
from app.models.tenant import Tenant, TenantUsageLog


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
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 30
    ) -> list[TenantUsageLog]:
        """获取租户用量日志"""
        query = select(TenantUsageLog).where(TenantUsageLog.tenant_id == tenant_id)

        if start_date:
            query = query.where(TenantUsageLog.usage_date >= start_date)
        if end_date:
            query = query.where(TenantUsageLog.usage_date <= end_date)

        query = query.order_by(TenantUsageLog.usage_date.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def record_daily_usage(self, tenant_id: str, usage_date: date | None = None) -> TenantUsageLog:
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
        from app.models.user import Patient

        day_start = datetime.combine(usage_date, datetime.min.time())
        day_end = datetime.combine(usage_date, datetime.max.time())

        # 通过患者所属门店统计
        result = await self.db.execute(
            select(func.count(Patient.id))
            .join(Store, Patient.store_id == Store.id)
            .where(
                and_(
                    Store.tenant_id == tenant_id,
                    Patient.created_at >= day_start,
                    Patient.created_at <= day_end
                )
            )
        )
        return result.scalar() or 0

    async def get_usage_trends(
        self,
        tenant_id: str,
        period_type: str = "week",
        periods: int = 8,
    ) -> dict:
        """获取租户用量趋势

        Args:
            tenant_id: 租户ID
            period_type: 周期类型 week/month
            periods: 返回几个周期

        Returns:
            包含趋势数据和环比变化率的字典
        """
        from app.modules.tenants.schemas import UsageTrendItem

        today = date.today()
        trends = []

        for i in range(periods - 1, -1, -1):
            if period_type == "month":
                # 计算月份起止
                target_month = today.month - i
                target_year = today.year
                while target_month <= 0:
                    target_month += 12
                    target_year -= 1
                period_start = date(target_year, target_month, 1)
                # 下月首日减一天
                if target_month == 12:
                    period_end = date(target_year + 1, 1, 1) - timedelta(days=1)
                else:
                    period_end = date(target_year, target_month + 1, 1) - timedelta(days=1)
                period_label = f"{target_year}-{target_month:02d}"
            else:
                # 计算周起止（周一开始）
                week_start = today - timedelta(days=today.weekday() + i * 7)
                period_start = week_start
                period_end = week_start + timedelta(days=6)
                period_label = f"{week_start.year}-W{week_start.isocalendar()[1]:02d}"

            # 聚合该周期内的用量日志
            stmt = select(
                func.coalesce(func.sum(TenantUsageLog.appointment_count), 0),
                func.coalesce(func.sum(TenantUsageLog.new_user_count), 0),
                func.coalesce(func.sum(TenantUsageLog.active_user_count), 0),
                func.coalesce(func.sum(TenantUsageLog.sms_sent_count), 0),
                func.coalesce(func.sum(TenantUsageLog.push_sent_count), 0),
                func.coalesce(func.max(TenantUsageLog.storage_used_mb), Decimal("0")),
            ).where(
                and_(
                    TenantUsageLog.tenant_id == tenant_id,
                    TenantUsageLog.usage_date >= period_start,
                    TenantUsageLog.usage_date <= period_end,
                )
            )
            result = await self.db.execute(stmt)
            row = result.one()

            trends.append(UsageTrendItem(
                period=period_label,
                appointment_count=row[0] or 0,
                new_user_count=row[1] or 0,
                active_user_count=row[2] or 0,
                sms_sent_count=row[3] or 0,
                push_sent_count=row[4] or 0,
                storage_used_mb=row[5] or Decimal("0"),
            ))

        # 计算环比变化率（最后两个周期）
        current = trends[-1] if trends else None
        previous = trends[-2] if len(trends) >= 2 else None

        def _change_rate(current_val, previous_val):
            if previous_val and previous_val > 0:
                return round((current_val - previous_val) / previous_val * 100, 2)
            return None

        return {
            "tenant_id": tenant_id,
            "period_type": period_type,
            "current_period": current,
            "previous_period": previous,
            "trends": trends,
            "appointment_change_rate": _change_rate(current.appointment_count, previous.appointment_count) if current and previous else None,
            "new_user_change_rate": _change_rate(current.new_user_count, previous.new_user_count) if current and previous else None,
            "active_user_change_rate": _change_rate(current.active_user_count, previous.active_user_count) if current and previous else None,
        }

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
