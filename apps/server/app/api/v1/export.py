"""数据导出 API - 已升级为 Excel 格式"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date
from io import BytesIO

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.services.export_service import ExportService

router = APIRouter()


@router.get("/appointments")
async def export_appointments(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[int] = None,
    doctor_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导出预约记录"""
    service = ExportService(db)
    excel_bytes, filename = await service.export_appointments(
        start_date=start_date,
        end_date=end_date,
        status=status,
        doctor_id=doctor_id,
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
    service = ExportService(db)
    excel_bytes, filename = await service.export_patients(keyword=keyword)
    
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
    service = ExportService(db)
    excel_bytes, filename = await service.export_schedules(
        start_date=start_date,
        end_date=end_date,
        doctor_id=doctor_id,
    )
    
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        }
    )
