"""联系人标签路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth_deps import get_current_admin
from app.common.permission_deps import require_permission
from app.db.session import get_db
from app.modules.contacts.schemas import TagCreate, TagResponse, TagUpdate
from app.modules.contacts.service import ContactTagService

router = APIRouter()


@router.get("", summary="获取标签列表")
async def list_tags(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:view")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ContactTagService(db)
    tags = await service.get_list(current_admin["tenant_id"])
    return [TagResponse.model_validate(t) for t in tags]


@router.post("", summary="创建标签")
async def create_tag(
    data: TagCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:create")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ContactTagService(db)
    tag = await service.create(
        data.model_dump(exclude_unset=True),
        tenant_id=current_admin["tenant_id"],
        created_by=current_admin.get("id"),
    )
    await db.commit()
    return TagResponse.model_validate(tag)


@router.put("/{tag_id}", summary="更新标签")
async def update_tag(
    tag_id: str,
    data: TagUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:edit")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ContactTagService(db)
    tag = await service.update(
        tag_id,
        data.model_dump(exclude_unset=True),
        tenant_id=current_admin["tenant_id"],
        updated_by=current_admin.get("id"),
    )
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")
    await db.commit()
    return TagResponse.model_validate(tag)


@router.delete("/{tag_id}", summary="删除标签")
async def delete_tag(
    tag_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:delete")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ContactTagService(db)
    success = await service.delete(tag_id, current_admin["tenant_id"])
    if not success:
        raise HTTPException(status_code=404, detail="标签不存在")
    await db.commit()
    return {"deleted": True}
