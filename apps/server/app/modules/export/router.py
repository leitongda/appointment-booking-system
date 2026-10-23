"""数据导出 API - 已升级为 Excel 格式"""
from datetime import date
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, require_admin_tenant_anchor
from app.common.deps import get_store_filter, require_permission
from app.common.feature_deps import require_feature
from app.db.session import get_db
from app.modules.export.service import ExportService

# R3-5：数据导出统一受租户 export_data 功能开关控制
# （FEATURE_ENFORCEMENT_ENABLED=False 时 require_feature 直接放行）
router = APIRouter(
    dependencies=[Depends(require_feature("export_data", get_current_admin))]
)


def _require_export_tenant(tenant_anchor: str | None) -> str:
    """R1-19：导出只认管理员账号锚点，平台管理员未指定租户时 400。"""
    if not tenant_anchor:
        raise HTTPException(
            status_code=400,
            detail="导出操作需要租户上下文，请指定 tenant_id 后重试",
        )
    return tenant_anchor


@router.get("/appointments", summary="导出预约记录")
async def export_appointments(
    start_date: date | None = None,
    end_date: date | None = None,
    status: int | None = None,
    doctor_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("appointment:export", "appointment:list")),
):
    """导出预约记录"""
    # 获取门店过滤条件
    store_ids = get_store_filter(current_admin)

    # R1-19：导出只认管理员账号锚点，不回退请求上下文
    tenant_id = _require_export_tenant(tenant_anchor)

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
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("patient:export", "patient:list")),
):
    """导出患者列表"""
    # R1-19：导出只认管理员账号锚点，不回退请求上下文
    tenant_id = _require_export_tenant(tenant_anchor)

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
    start_date: date | None = None,
    end_date: date | None = None,
    doctor_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("schedule:export", "schedule:list")),
):
    """导出排班记录"""
    # 获取门店过滤条件
    store_ids = get_store_filter(current_admin)

    # R1-19：导出只认管理员账号锚点，不回退请求上下文
    tenant_id = _require_export_tenant(tenant_anchor)

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
