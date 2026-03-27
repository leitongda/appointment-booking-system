"""数据导出 API - 已升级为 Excel 格式"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Union, List
from datetime import date
from io import BytesIO

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.common.deps import get_store_filter, get_tenant_filter
from app.modules.export.service import ExportService
from app.middleware.tenant_context import get_current_tenant_id

router = APIRouter()


@router.get("/appointments", summary="导出预约记录")
async def export_appointments(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[int] = None,
    doctor_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导出预约记录"""
    # 获取门店过滤条件
    store_ids = get_store_filter(current_admin)

    # 获取租户过滤条件
    tenant_id = get_tenant_filter(current_admin)
    if not tenant_id:
        tenant_id = get_current_tenant_id()

    service = ExportService(db)
    excel_bytes, filename = await service.export_appointments(
        start_date=start_date,
        end_date=end_date,
        status=status,
        doctor_id=doctor_id,
        store_ids=store_ids,
        tenant_id=tenant_id,
    )

    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        }
    )


@router.get("/patients")
async def export_patients(
    keyword: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导出患者列表"""
    # 获取租户过滤条件
    tenant_id = get_tenant_filter(current_admin)
    if not tenant_id:
        tenant_id = get_current_tenant_id()

    # 患者表没有 store_id，暂不进行门店过滤
    service = ExportService(db)
    excel_bytes, filename = await service.export_patients(keyword=keyword, tenant_id=tenant_id)

    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        }
    )


@router.get("/schedules")
async def export_schedules(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    doctor_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导出排班记录"""
    # 获取门店过滤条件
    store_ids = get_store_filter(current_admin)

    # 获取租户过滤条件
    tenant_id = get_tenant_filter(current_admin)
    if not tenant_id:
        tenant_id = get_current_tenant_id()

    service = ExportService(db)
    excel_bytes, filename = await service.export_schedules(
        start_date=start_date,
        end_date=end_date,
        doctor_id=doctor_id,
        store_ids=store_ids,
        tenant_id=tenant_id,
    )

    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        }
    )
