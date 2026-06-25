"""联系人分组路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth_deps import get_current_admin
from app.common.permission_deps import require_permission
from app.db.session import get_db
from app.modules.contacts.schemas import GroupCreate, GroupResponse, GroupTreeResponse, GroupUpdate
from app.modules.contacts.service import ContactGroupService

router = APIRouter()


def _build_tree(groups: list, parent_id: str | None = None) -> list[dict]:
    """构建树形结构"""
    tree = []
    for g in groups:
        if g.parent_id == parent_id:
            node = GroupTreeResponse(
                id=g.id,
                name=g.name,
                description=g.description,
                parent_id=g.parent_id,
                sort_order=g.sort_order,
                status=g.status,
                contact_count=len(g.contacts) if hasattr(g, 'contacts') and g.contacts else 0,
                children=_build_tree(groups, g.id),
            )
            tree.append(node)
    return tree


@router.get("", summary="获取分组列表（树形）")
async def list_groups(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:view")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ContactGroupService(db)
    groups = await service.get_tree(current_admin["tenant_id"])
    tree = _build_tree(groups)
    return tree


@router.post("", summary="创建分组")
async def create_group(
    data: GroupCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:create")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ContactGroupService(db)
    group = await service.create(
        data.model_dump(exclude_unset=True),
        tenant_id=current_admin["tenant_id"],
        created_by=current_admin.get("id"),
    )
    await db.commit()
    return GroupResponse.model_validate(group)


@router.put("/{group_id}", summary="更新分组")
async def update_group(
    group_id: str,
    data: GroupUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:edit")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ContactGroupService(db)
    group = await service.update(
        group_id,
        data.model_dump(exclude_unset=True),
        tenant_id=current_admin["tenant_id"],
        updated_by=current_admin.get("id"),
    )
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")
    await db.commit()
    return GroupResponse.model_validate(group)


@router.delete("/{group_id}", summary="删除分组")
async def delete_group(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:delete")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ContactGroupService(db)
    success = await service.delete(group_id, current_admin["tenant_id"])
    if not success:
        raise HTTPException(status_code=404, detail="分组不存在")
    await db.commit()
    return {"deleted": True}
