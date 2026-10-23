"""Admin management router."""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    check_store_access,
    get_current_admin,
    get_store_filter,
    require_admin_tenant_anchor,
    require_permission,
)
from app.core.config import settings
from app.db.session import get_db
from app.modules.admin.helpers import build_admin_response
from app.modules.admin.schemas import AdminCreate, AdminResponse, AdminUpdate
from app.modules.admin.service_admins import AdminService, TenantScopeError
from app.schemas.response import PageResponse

router = APIRouter()


def _require_admin_tenant(tenant_anchor: str | None) -> str:
    """R1-6：管理员管理端点必须拿到账号锚点，平台管理员未指定租户时 400。"""
    if not tenant_anchor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法确定租户ID，请指定 tenant_id 后重试",
        )
    return tenant_anchor


@router.get("/admins", response_model=PageResponse[AdminResponse], summary="获取管理员列表")
async def get_admins(
    role_id: str | None = None,
    status: int | None = None,
    keyword: str | None = None,
    store_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    service = AdminService(db)
    tenant_id = _require_admin_tenant(tenant_anchor)
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter
    items, total = await service.get_list(
        role_id=role_id,
        status=status,
        keyword=keyword,
        store_id=store_id,
        page=page,
        page_size=page_size,
        tenant_id=tenant_id,
    )
    return PageResponse(data=[build_admin_response(item) for item in items], total=total, page=page, page_size=page_size)


@router.get("/admins/{admin_id}", response_model=AdminResponse, summary="获取管理员详情")
async def get_admin(
    admin_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    service = AdminService(db)
    tenant_id = _require_admin_tenant(tenant_anchor)
    admin = await service.get_by_id(admin_id, tenant_id=tenant_id)
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在，请检查后重试")
    return build_admin_response(admin)


@router.post("/admins", response_model=AdminResponse, summary="创建管理员")
async def create_admin(
    data: AdminCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("system:user:create")),
):
    # R1-6：显式锚点优先（query/header），平台管理员也可用载荷 tenant_id 指定目标租户
    tenant_id = _require_admin_tenant(tenant_anchor or data.tenant_id)
    store_filter = get_store_filter(current_admin)
    if store_filter:
        if data.store_id and data.store_id != store_filter:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能在本门店创建用户，请选择正确的门店")
        data.store_id = store_filter

    # R1-6：锚点即目标租户，载荷 tenant_id 不得越过锚点
    if data.tenant_id is None:
        data.tenant_id = tenant_id
    elif data.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="禁止跨租户创建管理员")

    service = AdminService(db)
    try:
        admin = await service.create(data.model_dump(), actor=current_admin)
    except TenantScopeError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    admin = await service.get_by_id(admin.id, tenant_id=tenant_id)
    return build_admin_response(admin)


@router.put("/admins/{admin_id}", response_model=AdminResponse, summary="更新管理员")
async def update_admin(
    admin_id: str,
    data: AdminUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("system:user:update")),
):
    tenant_id = _require_admin_tenant(tenant_anchor)

    service = AdminService(db)
    admin = await service.get_by_id(admin_id, tenant_id=tenant_id)
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在，请检查后重试")

    # 租户校验：锚点之外的管理员一律拒绝
    if admin.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改其他租户的管理员")

    store_filter = get_store_filter(current_admin)
    if store_filter:
        target_store_ids = [s.id for s in (admin.stores or [])]
        if not target_store_ids and admin.current_store_id:
            target_store_ids = [admin.current_store_id]
        if not target_store_ids or not any(
            check_store_access(current_admin, target_store_id) for target_store_id in target_store_ids
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权修改此用户")
        if data.store_id and data.store_id != store_filter:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权修改用户的门店归属")

    try:
        await service.update(admin_id, data.model_dump(exclude_unset=True), tenant_id=tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    admin = await service.get_by_id(admin_id, tenant_id=tenant_id)
    return build_admin_response(admin)


@router.put("/admins/{admin_id}/reset-password", summary="重置密码")
async def reset_admin_password(
    admin_id: str,
    new_password: str = Query(..., min_length=6),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("system:user:reset-password")),
):
    tenant_id = _require_admin_tenant(tenant_anchor)
    service = AdminService(db)

    # 租户校验：锚点之外的管理员一律拒绝
    admin = await service.get_by_id(admin_id, tenant_id=tenant_id)
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在，请检查后重试")
    if admin.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权重置其他租户管理员的密码")

    success = await service.reset_password(admin_id, new_password, tenant_id=tenant_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在，请检查后重试")
    return {"message": "密码重置成功"}


@router.delete("/admins/{admin_id}", summary="删除管理员")
async def delete_admin(
    admin_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("system:user:delete")),
):
    tenant_id = _require_admin_tenant(tenant_anchor)
    service = AdminService(db)

    # 租户校验：锚点之外的管理员一律拒绝
    admin = await service.get_by_id(admin_id, tenant_id=tenant_id)
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在，请检查后重试")
    if admin.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权删除其他租户的管理员")

    try:
        success = await service.delete(admin_id, tenant_id=tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在，请检查后重试")
    return {"message": "删除成功"}
