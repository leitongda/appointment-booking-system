"""审批流定义路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.common.auth_unified import get_current_account_with_role
from app.common.permission_deps import require_permission
from app.modules.approval_flows.service_definitions import FlowDefinitionService
from app.modules.approval_flows.schemas import (
    FlowDefinitionCreate,
    FlowDefinitionUpdate,
    FlowDefinitionResponse,
    FlowDefinitionListResponse,
)

router = APIRouter()


@router.get("", summary="获取流程定义列表")
async def list_flow_definitions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    business_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("approval-flow:list")),
):
    service = FlowDefinitionService(db)
    items, total = await service.get_list(page, page_size, business_type, status)
    return {
        "items": [FlowDefinitionListResponse.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/by-business/{business_type}", summary="按业务类型获取激活流程")
async def get_by_business_type(
    business_type: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("approval-flow:list")),
):
    service = FlowDefinitionService(db)
    flow_def = await service.get_by_business_type(business_type)
    if not flow_def:
        return None
    return FlowDefinitionResponse.model_validate(flow_def)


@router.get("/{flow_def_id}", summary="获取流程定义详情")
async def get_flow_definition(
    flow_def_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("approval-flow:list")),
):
    service = FlowDefinitionService(db)
    flow_def = await service.get_by_id(flow_def_id)
    if not flow_def:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    return FlowDefinitionResponse.model_validate(flow_def)


@router.post("", summary="创建流程定义")
async def create_flow_definition(
    data: FlowDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    account=Depends(require_permission("approval-flow:create")),
):
    service = FlowDefinitionService(db)
    flow_def = await service.create(data, account.id)
    await db.commit()
    return FlowDefinitionResponse.model_validate(flow_def)


@router.put("/{flow_def_id}", summary="更新流程定义")
async def update_flow_definition(
    flow_def_id: str,
    data: FlowDefinitionUpdate,
    db: AsyncSession = Depends(get_db),
    account=Depends(require_permission("approval-flow:update")),
):
    service = FlowDefinitionService(db)
    try:
        flow_def = await service.update(flow_def_id, data, account.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not flow_def:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    await db.commit()
    return FlowDefinitionResponse.model_validate(flow_def)


@router.put("/{flow_def_id}/activate", summary="激活流程")
async def activate_flow(
    flow_def_id: str,
    db: AsyncSession = Depends(get_db),
    account=Depends(require_permission("approval-flow:manage")),
):
    service = FlowDefinitionService(db)
    try:
        flow_def = await service.activate(flow_def_id, account.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not flow_def:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    await db.commit()
    return FlowDefinitionResponse.model_validate(flow_def)


@router.put("/{flow_def_id}/archive", summary="归档流程")
async def archive_flow(
    flow_def_id: str,
    db: AsyncSession = Depends(get_db),
    account=Depends(require_permission("approval-flow:manage")),
):
    service = FlowDefinitionService(db)
    flow_def = await service.archive(flow_def_id, account.id)
    if not flow_def:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    await db.commit()
    return FlowDefinitionResponse.model_validate(flow_def)


@router.delete("/{flow_def_id}", summary="删除流程")
async def delete_flow(
    flow_def_id: str,
    db: AsyncSession = Depends(get_db),
    account=Depends(require_permission("approval-flow:delete")),
):
    service = FlowDefinitionService(db)
    try:
        result = await service.delete(flow_def_id, account.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    await db.commit()
    return {"deleted": True}


@router.post("/{flow_def_id}/copy", summary="复制流程定义")
async def copy_flow(
    flow_def_id: str,
    db: AsyncSession = Depends(get_db),
    account=Depends(require_permission("approval-flow:create")),
):
    service = FlowDefinitionService(db)
    flow_def = await service.copy(flow_def_id, account.id)
    if not flow_def:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    await db.commit()
    return FlowDefinitionResponse.model_validate(flow_def)
