"""CMS 栏目管理路由（树形）"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, require_permission
from app.db.session import get_db
from app.modules.cms.schemas import (
    CategoryCreate,
    CategoryResponse,
    CategoryTreeNode,
    CategoryUpdate,
    SortOrderRequest,
)
from app.modules.cms.service import CmsCategoryService
from app.utils.audit import get_operator_id_from_admin

router = APIRouter()


def _to_response(category) -> CategoryResponse:
    return CategoryResponse.model_validate(category)


def _serialize_tree(roots: list[dict]) -> list[CategoryTreeNode]:
    """把 service 构建的 {item, children} 结构序列化为树响应"""
    result: list[CategoryTreeNode] = []
    for node in roots:
        item = _to_response(node["item"])
        tree_node = CategoryTreeNode(**item.model_dump())
        tree_node.children = _serialize_tree(node["children"])
        result.append(tree_node)
    return result


@router.get("", response_model=list[CategoryResponse], summary="获取栏目列表")
async def list_categories(
    site_id: str | None = None,
    keyword: str | None = None,
    category_status: int | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(
        require_permission("cms:category", "cms:category:create", "cms:category:update", "cms:category:delete")
    ),
):
    service = CmsCategoryService(db)
    items = await service.get_list(
        tenant_id=current_admin["tenant_id"],
        site_id=site_id,
        keyword=keyword,
        status=category_status,
    )
    return [_to_response(item) for item in items]


@router.get("/tree", response_model=list[CategoryTreeNode], summary="获取栏目树")
async def get_category_tree(
    site_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:category")),
):
    service = CmsCategoryService(db)
    roots = await service.build_tree(tenant_id=current_admin["tenant_id"], site_id=site_id)
    return _serialize_tree(roots)


@router.get("/{category_id}", response_model=CategoryResponse, summary="获取栏目详情")
async def get_category(
    category_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:category")),
):
    service = CmsCategoryService(db)
    category = await service.get_by_id(category_id)
    if not category or category.tenant_id != current_admin["tenant_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="栏目不存在，请检查后重试")
    return _to_response(category)


@router.post("", response_model=CategoryResponse, summary="创建栏目")
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:category:create")),
):
    service = CmsCategoryService(db)
    category = await service.create(
        data.model_dump(exclude_unset=True),
        tenant_id=current_admin["tenant_id"],
        operator_id=get_operator_id_from_admin(current_admin),
    )
    return _to_response(category)


@router.put("/{category_id}", response_model=CategoryResponse, summary="更新栏目")
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:category:update")),
):
    service = CmsCategoryService(db)
    category = await service.update(
        category_id,
        data.model_dump(exclude_unset=True),
        operator_id=get_operator_id_from_admin(current_admin),
        tenant_id=current_admin["tenant_id"],
    )
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="栏目不存在，请检查后重试")
    return _to_response(category)


@router.delete("/{category_id}", summary="删除栏目")
async def delete_category(
    category_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:category:delete")),
):
    service = CmsCategoryService(db)
    success = await service.delete(category_id, tenant_id=current_admin["tenant_id"])
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="栏目不存在，请检查后重试")
    return {"message": "删除成功"}


@router.put("/sort", summary="批量排序栏目")
async def sort_categories(
    data: SortOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:category:update")),
):
    service = CmsCategoryService(db)
    updated = await service.batch_sort(
        [item.model_dump() for item in data.items],
        tenant_id=current_admin["tenant_id"],
    )
    return {"message": f"成功更新 {updated} 个栏目排序", "updated_count": updated}
