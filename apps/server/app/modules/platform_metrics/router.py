"""平台经营看台 - API 路由

全部需要平台管理员权限。前缀 /platform-metrics。
"""
from datetime import date
from io import BytesIO
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.common.deps import require_platform_admin
from app.schemas.response import ResponseModel
from app.infrastructure.excel.export_service import ExcelExportService
from app.modules.platform_metrics.service import PlatformMetricsService

router = APIRouter()


@router.get("/overview", response_model=ResponseModel, summary="全平台经营总览")
async def get_overview(
    start_date: Optional[date] = Query(None, alias="startDate"),
    end_date: Optional[date] = Query(None, alias="endDate"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin()),
):
    """全平台经营总览（默认近 30 天）。数据来源 store_daily_metrics 预聚合表。"""
    service = PlatformMetricsService(db)
    data = await service.overview(start_date=start_date, end_date=end_date)
    return ResponseModel(data=data)


@router.get("/tenants/compare", response_model=ResponseModel, summary="租户经营对比")
async def get_tenants_compare(
    start_date: Optional[date] = Query(None, alias="startDate"),
    end_date: Optional[date] = Query(None, alias="endDate"),
    sort_by: str = Query("revenue", description="排序字段: revenue/appointment/visit/new_patient"),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin()),
):
    """租户维度经营对比，按 sort_by 降序取 top N。"""
    service = PlatformMetricsService(db)
    data = await service.tenants_compare(
        start_date=start_date, end_date=end_date, sort_by=sort_by, limit=limit
    )
    return ResponseModel(data=data)


@router.get("/stores/compare", response_model=ResponseModel, summary="门店经营对比")
async def get_stores_compare(
    start_date: Optional[date] = Query(None, alias="startDate"),
    end_date: Optional[date] = Query(None, alias="endDate"),
    tenant_id: Optional[str] = Query(None, alias="tenantId", description="按租户过滤"),
    sort_by: str = Query("revenue", description="排序字段: revenue/appointment/visit/new_patient"),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin()),
):
    """门店维度经营对比，可按租户过滤，按 sort_by 降序取 top N。"""
    service = PlatformMetricsService(db)
    data = await service.stores_compare(
        start_date=start_date, end_date=end_date, tenant_id=tenant_id, sort_by=sort_by, limit=limit
    )
    return ResponseModel(data=data)


@router.get("/trend", response_model=ResponseModel, summary="平台整体趋势")
async def get_trend(
    start_date: Optional[date] = Query(None, alias="startDate"),
    end_date: Optional[date] = Query(None, alias="endDate"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin()),
):
    """平台整体趋势（默认近 30 天，按日聚合，补齐无数据日期）。"""
    service = PlatformMetricsService(db)
    data = await service.trend(start_date=start_date, end_date=end_date)
    return ResponseModel(data=data)


@router.get("/stores/export", summary="导出门店经营对比明细")
async def export_stores_compare(
    start_date: Optional[date] = Query(None, alias="startDate"),
    end_date: Optional[date] = Query(None, alias="endDate"),
    tenant_id: Optional[str] = Query(None, alias="tenantId"),
    sort_by: str = Query("revenue"),
    limit: int = Query(1000, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin()),
):
    """导出门店经营对比明细为 Excel。"""
    service = PlatformMetricsService(db)
    items = await service.stores_compare(
        start_date=start_date, end_date=end_date, tenant_id=tenant_id, sort_by=sort_by, limit=limit
    )

    headers = ["租户", "门店", "预约数", "已到院", "已完成", "爽约数", "爽约率(%)", "新患者数", "营收"]
    data = [
        [
            it.tenant_name or "",
            it.store_name or "",
            it.appointment_count,
            it.visit_count,
            it.completed_count,
            it.no_show_count,
            it.no_show_rate if it.no_show_rate is not None else "",
            it.new_patient_count,
            float(it.revenue),
        ]
        for it in items
    ]

    excel_bytes = ExcelExportService.create_workbook(
        headers=headers, data=data, sheet_name="门店经营对比"
    )
    filename = f"门店经营对比_{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
