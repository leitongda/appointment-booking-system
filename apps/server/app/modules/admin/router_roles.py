"""Admin roles router."""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, require_admin_tenant_anchor, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.modules.admin.helpers import build_role_response
from app.modules.admin.schemas import RoleCreate, RoleResponse, RoleUpdate
from app.modules.admin.service_roles import RoleService
from app.schemas.response import PageResponse

router = APIRouter()


@router.get("/roles", response_model=PageResponse[RoleResponse], summary="获取角色列表")
async def get_roles(
    status: int | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    tenant_filter: str | None = Depends(require_admin_tenant_anchor),
):
    # 租户隔离：传递 tenant_id 过滤条件
    service = RoleService(db)
    items, total = await service.get_list(
        status=status, keyword=keyword, page=page, page_size=page_size, tenant_id=tenant_filter,
    )
    return PageResponse(data=[build_role_response(item) for item in items], total=total, page=page, page_size=page_size)


@router.get("/roles/all", response_model=list[RoleResponse], summary="获取所有角色")
async def get_all_roles(
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    tenant_filter: str | None = Depends(require_admin_tenant_anchor),
):
    # 租户隔离：传递 tenant_id 过滤条件
    service = RoleService(db)
    items = await service.get_all(tenant_id=tenant_filter)
    return [build_role_response(item) for item in items]


@router.get("/roles/{role_id}", response_model=RoleResponse, summary="获取角色详情")
async def get_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    tenant_filter: str | None = Depends(require_admin_tenant_anchor),
):
    # 租户隔离：查询时附加租户过滤，防止跨租户访问
    service = RoleService(db)
    role = await service.get_by_id(role_id, tenant_id=tenant_filter)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在，请检查后重试")
    return build_role_response(role)


@router.post("/roles", response_model=RoleResponse, summary="创建角色")
async def create_role(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:role:create")),
    tenant_filter: str | None = Depends(require_admin_tenant_anchor),
):
    # 租户隔离：创建角色时设置 tenant_id
    service = RoleService(db)
    try:
        role = await service.create(data.model_dump(), tenant_id=tenant_filter)
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
    tenant_filter: str | None = Depends(require_admin_tenant_anchor),
):
    # 租户隔离：更新时附加租户过滤，防止跨租户修改
    service = RoleService(db)
    try:
        role = await service.update(role_id, data.model_dump(exclude_unset=True), tenant_id=tenant_filter)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在，请检查后重试")
    return build_role_response(role)


@router.put("/roles/{role_id}/permissions", summary="更新角色权限")
async def update_role_permissions(
    role_id: str,
    permissions: list[str],
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:role:permission")),
    tenant_filter: str | None = Depends(require_admin_tenant_anchor),
):
    # 租户隔离：校验角色属于当前租户后再更新权限
    service = RoleService(db)
    role = await service.update_permissions(role_id, permissions, tenant_id=tenant_filter)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在，请检查后重试")
    return {"message": "权限更新成功"}


@router.delete("/roles/{role_id}", summary="删除角色")
async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:role:delete")),
    tenant_filter: str | None = Depends(require_admin_tenant_anchor),
):
    # 租户隔离：删除时附加租户过滤，防止跨租户删除
    service = RoleService(db)
    try:
        success = await service.delete(role_id, tenant_id=tenant_filter)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在，请检查后重试")
    return {"message": "删除成功"}
