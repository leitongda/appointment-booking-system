"""Admin permissions router."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.common.deps import require_permission
from app.db.session import get_db
from app.modules.admin.schemas import PermissionCreate
from app.modules.admin.service_permissions import PermissionService

router = APIRouter()


@router.get("/permissions/tree", summary="获取权限树")
async def get_permissions_tree(
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("system:role:permission")),
):
    service = PermissionService(db)
    return await service.get_tree()


@router.get("/permissions/all", summary="获取所有权限")
async def get_all_permissions(
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("system:role:permission")),
):
    service = PermissionService(db)
    permissions = await service.get_all()
    return [
        {
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "type": p.type,
            "controlType": p.control_type,
            "parentCode": p.parent_code,
            "icon": p.icon,
            "sort": p.sort,
        }
        for p in permissions
    ]


@router.post("/permissions", summary="创建权限")
async def create_permission(
    data: PermissionCreate,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("system:role:permission")),
):
    service = PermissionService(db)
    try:
        permission = await service.create(data.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "id": permission.id,
        "code": permission.code,
        "name": permission.name,
        "type": permission.type,
        "controlType": permission.control_type,
        "parentCode": permission.parent_code,
        "icon": permission.icon,
        "sort": permission.sort,
    }


@router.post("/permissions/batch", summary="批量创建权限")
async def batch_create_permissions(
    permissions: List[PermissionCreate],
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("system:role:permission")),
):
    service = PermissionService(db)
    created = await service.batch_create([p.model_dump() for p in permissions])
    return {"message": f"成功创建 {len(created)} 条权限"}


@router.delete("/permissions/{code}", summary="删除权限")
async def delete_permission(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("system:role:permission")),
):
    service = PermissionService(db)
    success = await service.delete(code)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="权限不存在，请检查后重试")
    return {"message": "删除成功"}
