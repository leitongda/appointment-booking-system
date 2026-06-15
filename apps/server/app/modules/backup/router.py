"""租户数据备份恢复路由"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import require_platform_admin
from app.db.session import get_db
from app.modules.backup.service import BackupService

router = APIRouter()


@router.post("/{tenant_id}/export", summary="导出租户数据备份")
async def export_tenant_backup(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin()),
):
    """导出租户全部数据为 JSON（仅平台管理员）"""
    import io
    import json

    from fastapi.responses import StreamingResponse

    service = BackupService(db)
    try:
        result = await service.export_tenant_data(tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    content = json.dumps(result, ensure_ascii=False, indent=2)
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=tenant_{tenant_id[:8]}_backup.json"},
    )


@router.post("/{tenant_id}/import/precheck", summary="导入前预检")
async def precheck_tenant_import(
    tenant_id: str,
    file: UploadFile = File(..., description="备份 JSON 文件"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin()),
):
    """检查备份数据与目标租户的 ID 冲突（仅平台管理员）"""
    import json

    content = await file.read()
    try:
        backup_data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的 JSON 文件")

    service = BackupService(db)
    try:
        return await service.precheck_import(tenant_id, backup_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{tenant_id}/import", summary="导入租户数据恢复")
async def import_tenant_backup(
    tenant_id: str,
    file: UploadFile = File(..., description="备份 JSON 文件"),
    overwrite: bool = False,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin()),
):
    """导入备份数据恢复到指定租户（仅平台管理员）"""
    import json

    content = await file.read()
    try:
        backup_data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的 JSON 文件")

    service = BackupService(db)
    try:
        result = await service.import_tenant_data(
            tenant_id, backup_data,
            overwrite=overwrite,
            actor_id=current_admin.get("id"),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
