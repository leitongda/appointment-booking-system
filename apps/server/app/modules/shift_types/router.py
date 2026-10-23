"""
班次类型管理 API

提供班次类型的 CRUD 接口
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_admin,
    get_current_super_admin,
    require_admin_tenant_anchor,
)
from app.core.config import settings
from app.db.session import get_db
from app.modules.shift_types.schemas import ShiftTypeCreate, ShiftTypeResponse, ShiftTypeUpdate
from app.modules.shift_types.service import ShiftTypeService
from app.schemas.rule_set import PageResult

router = APIRouter()


@router.get("", response_model=PageResult[ShiftTypeResponse], summary="获取班次类型列表")
async def get_shift_types(
    enabled: bool | None = Query(None, description="是否启用"),
    keyword: str | None = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """获取班次类型列表"""
    service = ShiftTypeService(db)
    shift_types, total = await service.get_list(
        enabled=enabled,
        keyword=keyword,
        page=page,
        page_size=page_size,
        tenant_id=tenant_anchor,
    )
    return PageResult(data=shift_types, total=total)


@router.get("/all", response_model=list[ShiftTypeResponse], summary="获取所有启用班次类型")
async def get_all_shift_types(
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """获取所有启用的班次类型（用于下拉选择）"""
    service = ShiftTypeService(db)
    shift_types = await service.get_all_enabled(tenant_id=tenant_anchor)
    return shift_types


@router.get("/{shift_type_id}", response_model=ShiftTypeResponse, summary="获取班次类型详情")
async def get_shift_type(
    shift_type_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """获取班次类型详情"""
    service = ShiftTypeService(db)
    shift_type = await service.get_by_id(shift_type_id, tenant_id=tenant_anchor)
    if not shift_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="班次类型不存在"
        )
    return shift_type


@router.post("", response_model=ShiftTypeResponse, status_code=status.HTTP_201_CREATED, summary="创建班次类型")
async def create_shift_type(
    data: ShiftTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_super_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """创建班次类型（仅超级管理员）"""
    service = ShiftTypeService(db)
    try:
        shift_type = await service.create(
            code=data.code,
            name=data.name,
            description=data.description,
            enabled=data.enabled,
            operator_id=current_user["id"],
            tenant_id=tenant_anchor,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    return shift_type


@router.put("/{shift_type_id}", response_model=ShiftTypeResponse, summary="更新班次类型")
async def update_shift_type(
    shift_type_id: str,
    data: ShiftTypeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_super_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """更新班次类型（仅超级管理员）"""
    service = ShiftTypeService(db)
    shift_type = await service.update(
        shift_type_id=shift_type_id,
        name=data.name,
        description=data.description,
        enabled=data.enabled,
        operator_id=current_user["id"],
        tenant_id=tenant_anchor,
    )
    if not shift_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="班次类型不存在"
        )
    return shift_type


@router.delete("/{shift_type_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除班次类型")
async def delete_shift_type(
    shift_type_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_super_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """删除班次类型（仅超级管理员）"""
    service = ShiftTypeService(db)
    success = await service.delete(shift_type_id, tenant_id=tenant_anchor)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="班次类型不存在"
        )
    return None
