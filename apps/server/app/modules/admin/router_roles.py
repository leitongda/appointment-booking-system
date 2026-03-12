"""Admin roles and permissions router."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.modules.admin.helpers import build_role_response
from app.modules.admin.schemas import PermissionCreate, RoleCreate, RoleResponse, RoleUpdate
from app.schemas.response import PageResponse
from app.services.admin_service import PermissionService, RoleService

router = APIRouter()


@router.get("/roles", response_model=PageResponse[RoleResponse], summary="获取角色列表")
async def get_roles(
    status: Optional[int] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    service = RoleService(db)
    items, total = await service.get_list(status=status, keyword=keyword, page=page, page_size=page_size)
    return PageResponse(data=[build_role_response(item) for item in items], total=total, page=page, page_size=page_size)


@router.get("/roles/all", response_model=List[RoleResponse], summary="获取所有角色")
async def get_all_roles(
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    service = RoleService(db)
    items = await service.get_all()
    return [build_role_response(item) for item in items]


@router.get("/roles/{role_id}", response_model=RoleResponse, summary="获取角色详情")
async def get_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    service = RoleService(db)
    role = await service.get_by_id(role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在，请检查后重试")
    return build_role_response(role)


@router.post("/roles", response_model=RoleResponse, summary="创建角色")
async def create_role(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:role:create")),
):
    service = RoleService(db)
    try:
        role = await service.create(data.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return build_role_response(role)


@router.put("/roles/{role_id}", response_model=RoleResponse, summary="更新角色")
async def update_role(
    role_id: str,
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:role:update")),
):
    service = RoleService(db)
    try:
        role = await service.update(role_id, data.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在，请检查后重试")
    return build_role_response(role)


@router.put("/roles/{role_id}/permissions", summary="更新角色权限")
async def update_role_permissions(
    role_id: str,
    permissions: List[str],
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:role:permission")),
):
    service = RoleService(db)
    role = await service.update_permissions(role_id, permissions)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在，请检查后重试")
    return {"message": "权限更新成功"}


@router.delete("/roles/{role_id}", summary="删除角色")
async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:role:delete")),
):
    service = RoleService(db)
    try:
        success = await service.delete(role_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在，请检查后重试")
    return {"message": "删除成功"}


@router.get("/permissions/tree", summary="获取权限树")
async def get_permissions_tree(
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    service = PermissionService(db)
    return await service.get_tree()


@router.get("/permissions/all", summary="获取所有权限")
async def get_all_permissions(
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    service = PermissionService(db)
    permissions = await service.get_all()
    return [
        {
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "type": p.type,
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
        "parentCode": permission.parent_code,
        "icon": permission.icon,
        "sort": permission.sort,
    }


@router.post("/permissions/batch", summary="批量创建权限")
async def batch_create_permissions(
    permissions: List[PermissionCreate],
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    service = PermissionService(db)
    created = await service.batch_create([p.model_dump() for p in permissions])
    return {"message": f"成功创建 {len(created)} 条权限"}


@router.delete("/permissions/{code}", summary="删除权限")
async def delete_permission(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    service = PermissionService(db)
    success = await service.delete(code)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="权限不存在，请检查后重试")
    return {"message": "删除成功"}
