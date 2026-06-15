"""平台经营看台 - 响应 Schema"""
from datetime import date
from decimal import Decimal

from pydantic import Field

from app.schemas.base import BaseSchema


class PlatformOverview(BaseSchema):
    """全平台经营总览"""
    start_date: date = Field(..., alias="startDate")
    end_date: date = Field(..., alias="endDate")
    tenant_count: int = Field(0, alias="tenantCount", description="涉及租户数（去重）")
    active_store_count: int = Field(0, alias="activeStoreCount", description="有数据的门店数（去重）")
    appointment_count: int = Field(0, alias="appointmentCount")
    visit_count: int = Field(0, alias="visitCount", description="已到院数")
    completed_count: int = Field(0, alias="completedCount")
    no_show_count: int = Field(0, alias="noShowCount")
    cancelled_count: int = Field(0, alias="cancelledCount")
    new_patient_count: int = Field(0, alias="newPatientCount")
    revenue: Decimal = Field(Decimal("0"), description="营收（诊费累计）")
    no_show_rate: float | None = Field(None, alias="noShowRate", description="爽约率 = 爽约/(已到院+爽约)")


class TenantCompareItem(BaseSchema):
    tenant_id: str | None = Field(None, alias="tenantId")
    tenant_name: str | None = Field(None, alias="tenantName")
    store_count: int = Field(0, alias="storeCount")
    appointment_count: int = Field(0, alias="appointmentCount")
    visit_count: int = Field(0, alias="visitCount")
    completed_count: int = Field(0, alias="completedCount")
    no_show_count: int = Field(0, alias="noShowCount")
    new_patient_count: int = Field(0, alias="newPatientCount")
    revenue: Decimal = Field(Decimal("0"))
    no_show_rate: float | None = Field(None, alias="noShowRate")


class StoreCompareItem(BaseSchema):
    store_id: str = Field(..., alias="storeId")
    store_name: str | None = Field(None, alias="storeName")
    tenant_id: str | None = Field(None, alias="tenantId")
    tenant_name: str | None = Field(None, alias="tenantName")
    appointment_count: int = Field(0, alias="appointmentCount")
    visit_count: int = Field(0, alias="visitCount")
    completed_count: int = Field(0, alias="completedCount")
    no_show_count: int = Field(0, alias="noShowCount")
    new_patient_count: int = Field(0, alias="newPatientCount")
    revenue: Decimal = Field(Decimal("0"))
    no_show_rate: float | None = Field(None, alias="noShowRate")


class TrendPoint(BaseSchema):
    date: date
    appointment_count: int = Field(0, alias="appointmentCount")
    visit_count: int = Field(0, alias="visitCount")
    completed_count: int = Field(0, alias="completedCount")
    new_patient_count: int = Field(0, alias="newPatientCount")
    revenue: Decimal = Field(Decimal("0"))


def calc_no_show_rate(visit_count: int, no_show_count: int) -> float | None:
    """爽约率 = 爽约 / (已到院 + 爽约)，无数据返回 None"""
    denom = visit_count + no_show_count
    if denom <= 0:
        return None
    return round(no_show_count / denom * 100, 2)
