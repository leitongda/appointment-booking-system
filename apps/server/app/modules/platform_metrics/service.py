"""平台经营看台 - 数据服务

全部基于 store_daily_metrics 预聚合表，不触碰业务库。
"""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store
from app.models.store_metric import StoreDailyMetric
from app.models.tenant import Tenant
from app.modules.platform_metrics.schemas import (
    PlatformOverview,
    StoreCompareItem,
    TenantCompareItem,
    TrendPoint,
    calc_no_show_rate,
)


def _default_range(end_date: date | None, days: int = 30) -> tuple[date, date]:
    end = end_date or date.today() - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    return start, end


class PlatformMetricsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def overview(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> PlatformOverview:
        start, end = _default_range(end_date) if not start_date else (start_date, end_date or date.today())

        row = (
            await self.db.execute(
                select(
                    func.count(func.distinct(StoreDailyMetric.store_id)).label("active_stores"),
                    func.count(func.distinct(StoreDailyMetric.tenant_id)).label("tenant_count"),
                    func.coalesce(func.sum(StoreDailyMetric.appointment_count), 0).label("appointments"),
                    func.coalesce(func.sum(StoreDailyMetric.visit_count), 0).label("visits"),
                    func.coalesce(func.sum(StoreDailyMetric.completed_count), 0).label("completed"),
                    func.coalesce(func.sum(StoreDailyMetric.no_show_count), 0).label("no_show"),
                    func.coalesce(func.sum(StoreDailyMetric.cancelled_count), 0).label("cancelled"),
                    func.coalesce(func.sum(StoreDailyMetric.new_patient_count), 0).label("new_patients"),
                    func.coalesce(func.sum(StoreDailyMetric.revenue), 0).label("revenue"),
                ).where(
                    and_(
                        StoreDailyMetric.stat_date >= start,
                        StoreDailyMetric.stat_date <= end,
                    )
                )
            )
        ).one()

        visits = int(row.visits or 0)
        no_show = int(row.no_show or 0)
        return PlatformOverview(
            startDate=start,
            endDate=end,
            tenantCount=int(row.tenant_count or 0),
            activeStoreCount=int(row.active_stores or 0),
            appointmentCount=int(row.appointments or 0),
            visitCount=visits,
            completedCount=int(row.completed or 0),
            noShowCount=no_show,
            cancelledCount=int(row.cancelled or 0),
            newPatientCount=int(row.new_patients or 0),
            revenue=Decimal(row.revenue or 0),
            noShowRate=calc_no_show_rate(visits, no_show),
        )

    async def tenants_compare(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        sort_by: str = "revenue",
        limit: int = 50,
    ) -> list[TenantCompareItem]:
        start, end = _default_range(end_date) if not start_date else (start_date, end_date or date.today())

        sum_col = {
            "revenue": func.sum(StoreDailyMetric.revenue),
            "appointment": func.sum(StoreDailyMetric.appointment_count),
            "visit": func.sum(StoreDailyMetric.visit_count),
            "new_patient": func.sum(StoreDailyMetric.new_patient_count),
        }.get(sort_by, func.sum(StoreDailyMetric.revenue))

        rows = (
            await self.db.execute(
                select(
                    StoreDailyMetric.tenant_id.label("tenant_id"),
                    func.max(Tenant.name).label("tenant_name"),
                    func.count(func.distinct(StoreDailyMetric.store_id)).label("store_count"),
                    func.coalesce(func.sum(StoreDailyMetric.appointment_count), 0).label("appointments"),
                    func.coalesce(func.sum(StoreDailyMetric.visit_count), 0).label("visits"),
                    func.coalesce(func.sum(StoreDailyMetric.completed_count), 0).label("completed"),
                    func.coalesce(func.sum(StoreDailyMetric.no_show_count), 0).label("no_show"),
                    func.coalesce(func.sum(StoreDailyMetric.new_patient_count), 0).label("new_patients"),
                    func.coalesce(func.sum(StoreDailyMetric.revenue), 0).label("revenue"),
                )
                .select_from(StoreDailyMetric)
                .outerjoin(Tenant, StoreDailyMetric.tenant_id == Tenant.id)
                .where(and_(
                    StoreDailyMetric.stat_date >= start,
                    StoreDailyMetric.stat_date <= end,
                ))
                .group_by(StoreDailyMetric.tenant_id)
                .order_by(desc(sum_col))
                .limit(limit)
            )
        ).all()

        result = []
        for r in rows:
            visits = int(r.visits or 0)
            no_show = int(r.no_show or 0)
            result.append(TenantCompareItem(
                tenantId=r.tenant_id,
                tenantName=r.tenant_name or "平台级门店",
                storeCount=int(r.store_count or 0),
                appointmentCount=int(r.appointments or 0),
                visitCount=visits,
                completedCount=int(r.completed or 0),
                noShowCount=no_show,
                newPatientCount=int(r.new_patients or 0),
                revenue=Decimal(r.revenue or 0),
                noShowRate=calc_no_show_rate(visits, no_show),
            ))
        return result

    async def stores_compare(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        tenant_id: str | None = None,
        sort_by: str = "revenue",
        limit: int = 100,
    ) -> list[StoreCompareItem]:
        start, end = _default_range(end_date) if not start_date else (start_date, end_date or date.today())

        sum_col = {
            "revenue": func.sum(StoreDailyMetric.revenue),
            "appointment": func.sum(StoreDailyMetric.appointment_count),
            "visit": func.sum(StoreDailyMetric.visit_count),
            "new_patient": func.sum(StoreDailyMetric.new_patient_count),
        }.get(sort_by, func.sum(StoreDailyMetric.revenue))

        conditions = [
            StoreDailyMetric.stat_date >= start,
            StoreDailyMetric.stat_date <= end,
        ]
        if tenant_id:
            conditions.append(StoreDailyMetric.tenant_id == tenant_id)

        rows = (
            await self.db.execute(
                select(
                    StoreDailyMetric.store_id.label("store_id"),
                    func.max(Store.name).label("store_name"),
                    StoreDailyMetric.tenant_id.label("tenant_id"),
                    func.max(Tenant.name).label("tenant_name"),
                    func.coalesce(func.sum(StoreDailyMetric.appointment_count), 0).label("appointments"),
                    func.coalesce(func.sum(StoreDailyMetric.visit_count), 0).label("visits"),
                    func.coalesce(func.sum(StoreDailyMetric.completed_count), 0).label("completed"),
                    func.coalesce(func.sum(StoreDailyMetric.no_show_count), 0).label("no_show"),
                    func.coalesce(func.sum(StoreDailyMetric.new_patient_count), 0).label("new_patients"),
                    func.coalesce(func.sum(StoreDailyMetric.revenue), 0).label("revenue"),
                )
                .select_from(StoreDailyMetric)
                .outerjoin(Store, StoreDailyMetric.store_id == Store.id)
                .outerjoin(Tenant, StoreDailyMetric.tenant_id == Tenant.id)
                .where(and_(*conditions))
                .group_by(StoreDailyMetric.store_id, StoreDailyMetric.tenant_id)
                .order_by(desc(sum_col))
                .limit(limit)
            )
        ).all()

        result = []
        for r in rows:
            visits = int(r.visits or 0)
            no_show = int(r.no_show or 0)
            result.append(StoreCompareItem(
                storeId=r.store_id,
                storeName=r.store_name or "未知门店",
                tenantId=r.tenant_id,
                tenantName=r.tenant_name,
                appointmentCount=int(r.appointments or 0),
                visitCount=visits,
                completedCount=int(r.completed or 0),
                noShowCount=no_show,
                newPatientCount=int(r.new_patients or 0),
                revenue=Decimal(r.revenue or 0),
                noShowRate=calc_no_show_rate(visits, no_show),
            ))
        return result

    async def trend(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[TrendPoint]:
        start, end = _default_range(end_date) if not start_date else (start_date, end_date or date.today())

        rows = (
            await self.db.execute(
                select(
                    StoreDailyMetric.stat_date.label("d"),
                    func.coalesce(func.sum(StoreDailyMetric.appointment_count), 0).label("appointments"),
                    func.coalesce(func.sum(StoreDailyMetric.visit_count), 0).label("visits"),
                    func.coalesce(func.sum(StoreDailyMetric.completed_count), 0).label("completed"),
                    func.coalesce(func.sum(StoreDailyMetric.new_patient_count), 0).label("new_patients"),
                    func.coalesce(func.sum(StoreDailyMetric.revenue), 0).label("revenue"),
                )
                .where(and_(
                    StoreDailyMetric.stat_date >= start,
                    StoreDailyMetric.stat_date <= end,
                ))
                .group_by(StoreDailyMetric.stat_date)
                .order_by(asc(StoreDailyMetric.stat_date))
            )
        ).all()

        # 补齐无数据日期，保证趋势连续
        by_date = {r.d: r for r in rows}
        points = []
        cur = start
        while cur <= end:
            r = by_date.get(cur)
            if r:
                points.append(TrendPoint(
                    date=cur,
                    appointmentCount=int(r.appointments or 0),
                    visitCount=int(r.visits or 0),
                    completedCount=int(r.completed or 0),
                    newPatientCount=int(r.new_patients or 0),
                    revenue=Decimal(r.revenue or 0),
                ))
            else:
                points.append(TrendPoint(date=cur))
            cur += timedelta(days=1)
        return points
