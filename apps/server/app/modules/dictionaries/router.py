"""字典管理 API

提供字典类型和字典项的 CRUD 接口，以及公开查询接口。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, require_admin_tenant_anchor
from app.core.config import settings
from app.db.session import get_db
from app.modules.dictionaries.schemas import (
    DictItemCreate,
    DictItemResponse,
    DictItemUpdate,
    DictTypeCreate,
    DictTypeResponse,
    DictTypeUpdate,
    SortRequest,
)
from app.modules.dictionaries.service import DictService
from app.schemas.rule_set import PageResult

router = APIRouter()


def _require_anchor(tenant_anchor: str | None) -> str:
    """R1-15：字典写路径必须拿到账号锚点，禁止写出 tenant_id=NULL 的记录。"""
    if not tenant_anchor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法确定租户ID，请指定 tenant_id 后重试",
        )
    return tenant_anchor


# ==================== 管理 API（admin 端） ====================


@router.get("", response_model=PageResult[DictTypeResponse], summary="获取字典类型列表")
async def get_dict_types(
    status_: int | None = Query(None, alias="status", description="状态 1=启用 0=禁用"),
    keyword: str | None = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """获取字典类型列表"""
    service = DictService(db, tenant_id=tenant_anchor)
    items, total = await service.get_type_list(
        status=status_,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PageResult(data=items, total=total)


@router.get("/{type_id}", response_model=DictTypeResponse, summary="获取字典类型详情")
async def get_dict_type(
    type_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """获取字典类型详情"""
    service = DictService(db, tenant_id=tenant_anchor)
    dict_type = await service.get_type_by_id(type_id)
    if not dict_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="字典类型不存在",
        )
    return dict_type


@router.post(
    "",
    response_model=DictTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建字典类型",
)
async def create_dict_type(
    data: DictTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """创建字典类型"""
    service = DictService(db, tenant_id=_require_anchor(tenant_anchor))
    try:
        dict_type = await service.create_type(
            code=data.code,
            name=data.name,
            description=data.description,
            operator_id=current_admin.get("id"),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return dict_type


@router.put("/{type_id}", response_model=DictTypeResponse, summary="更新字典类型")
async def update_dict_type(
    type_id: str,
    data: DictTypeUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """更新字典类型"""
    service = DictService(db, tenant_id=_require_anchor(tenant_anchor))
    dict_type = await service.update_type(
        type_id=type_id,
        name=data.name,
        description=data.description,
        status=data.status,
        operator_id=current_admin.get("id"),
    )
    if not dict_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="字典类型不存在",
        )
    return dict_type


@router.delete("/{type_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除字典类型")
async def delete_dict_type(
    type_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """删除字典类型（软删除：禁用）"""
    service = DictService(db, tenant_id=_require_anchor(tenant_anchor))
    success = await service.delete_type(type_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="字典类型不存在",
        )
    return None


# ==================== 字典项管理 API ====================


@router.get(
    "/{type_id}/items",
    response_model=PageResult[DictItemResponse],
    summary="获取字典项列表",
)
async def get_dict_items(
    type_id: str,
    status_: int | None = Query(None, alias="status", description="状态"),
    keyword: str | None = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """获取字典项列表"""
    service = DictService(db, tenant_id=tenant_anchor)
    items, total = await service.get_items(
        type_id=type_id,
        status=status_,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PageResult(data=items, total=total)


@router.post(
    "/{type_id}/items",
    response_model=DictItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建字典项",
)
async def create_dict_item(
    type_id: str,
    data: DictItemCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """创建字典项"""
    service = DictService(db, tenant_id=_require_anchor(tenant_anchor))

    # 验证字典类型存在
    dict_type = await service.get_type_by_id(type_id)
    if not dict_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="字典类型不存在",
        )

    item = await service.create_item(
        type_id=type_id,
        label=data.label,
        value=data.value,
        sort_order=data.sort_order,
        extra=data.extra,
        operator_id=current_admin.get("id"),
    )
    return item


@router.put(
    "/{type_id}/items/{item_id}",
    response_model=DictItemResponse,
    summary="更新字典项",
)
async def update_dict_item(
    type_id: str,
    item_id: str,
    data: DictItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """更新字典项"""
    service = DictService(db, tenant_id=_require_anchor(tenant_anchor))
    item = await service.update_item(
        item_id=item_id,
        label=data.label,
        value=data.value,
        sort_order=data.sort_order,
        status=data.status,
        extra=data.extra,
        operator_id=current_admin.get("id"),
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="字典项不存在",
        )
    return item


@router.delete(
    "/{type_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除字典项",
)
async def delete_dict_item(
    type_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """删除字典项（软删除：禁用）"""
    service = DictService(db, tenant_id=_require_anchor(tenant_anchor))
    success = await service.delete_item(item_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="字典项不存在",
        )
    return None


@router.put("/{type_id}/items-sort", summary="批量排序字典项")
async def sort_dict_items(
    type_id: str,
    data: SortRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """批量更新字典项排序"""
    service = DictService(db, tenant_id=_require_anchor(tenant_anchor))
    items = [{"id": item.id, "sort_order": item.sort_order} for item in data.items]
    await service.sort_items(items)
    return {"message": "排序成功"}
