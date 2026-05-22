"""审批实例路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.common.auth_unified import get_current_account_with_role
from app.common.permission_deps import require_permission
from app.modules.approval_flows.service_instances import ApprovalInstanceService
from app.modules.approval_flows.schemas import (
    ApprovalInstanceResponse,
    ApprovalInstanceListResponse,
    ApprovalActionRequest,
    ApprovalDelegateRequest,
    ApprovalQuery,
)

router = APIRouter()


@router.get("", summary="获取审批实例列表")
async def list_instances(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    business_type: Optional[str] = None,
    store_id: Optional[str] = None,
    view: str = Query("pending", description="pending=我的待办, done=我的已办, initiated=我发起的"),
    db: AsyncSession = Depends(get_db),
    account=Depends(require_permission("approval:read")),
):
    query = ApprovalQuery(
        page=page,
        page_size=page_size,
        status=status,
        business_type=business_type,
        store_id=store_id,
    )
    service = ApprovalInstanceService(db)

    items, total = await service.get_list(query, account.id, view)

    return {
        "items": [ApprovalInstanceListResponse.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/my-pending", summary="获取我的待办列表（兼容旧前端）")
async def list_my_pending_instances(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    business_type: Optional[str] = None,
    store_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    account=Depends(require_permission("approval:read")),
):
    query = ApprovalQuery(
        page=page,
        page_size=page_size,
        business_type=business_type,
        store_id=store_id,
    )
    service = ApprovalInstanceService(db)
    items, total = await service.get_list(query, account.id, "pending")

    return {
        "items": [ApprovalInstanceListResponse.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/pending-count", summary="获取待办数量")
async def get_pending_count(
    db: AsyncSession = Depends(get_db),
    account=Depends(require_permission("approval:read")),
):
    service = ApprovalInstanceService(db)
    count = await service.get_pending_count(account.id)
    return {"count": count}


@router.get("/by-business/{business_type}/{business_id}", summary="按业务 ID 获取审批状态")
async def get_by_business(
    business_type: str,
    business_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("approval:read")),
):
    service = ApprovalInstanceService(db)
    instance = await service.get_by_business(business_type, business_id)
    if not instance:
        return None
    return ApprovalInstanceResponse.model_validate(instance)


@router.get("/{instance_id}", summary="获取审批实例详情")
async def get_instance(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("approval:read")),
):
    service = ApprovalInstanceService(db)
    instance = await service.get_by_id(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="审批实例不存在")
    return ApprovalInstanceResponse.model_validate(instance)


@router.get("/{instance_id}/progress", summary="获取审批进度")
async def get_progress(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("approval:read")),
):
    service = ApprovalInstanceService(db)
    progress = await service.get_progress(instance_id)
    return progress


@router.post("/{instance_id}/approve", summary="审批通过")
async def approve_instance(
    instance_id: str,
    data: ApprovalActionRequest = ApprovalActionRequest(),
    db: AsyncSession = Depends(get_db),
    account=Depends(require_permission("approval:approve")),
):
    service = ApprovalInstanceService(db)
    try:
        instance = await service.approve(
            instance_id, account.id, account.name or "", data.comment
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return ApprovalInstanceResponse.model_validate(instance)


@router.post("/{instance_id}/reject", summary="审批拒绝")
async def reject_instance(
    instance_id: str,
    data: ApprovalActionRequest = ApprovalActionRequest(),
    db: AsyncSession = Depends(get_db),
    account=Depends(require_permission("approval:approve")),
):
    service = ApprovalInstanceService(db)
    try:
        instance = await service.reject(
            instance_id, account.id, account.name or "", data.comment
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return ApprovalInstanceResponse.model_validate(instance)


@router.post("/{instance_id}/delegate", summary="转交")
async def delegate_instance(
    instance_id: str,
    data: ApprovalDelegateRequest,
    db: AsyncSession = Depends(get_db),
    account=Depends(require_permission("approval:approve")),
):
    service = ApprovalInstanceService(db)
    try:
        instance = await service.delegate(
            instance_id, account.id, account.name or "",
            data.target_user_id, data.target_user_name or "", data.comment,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return ApprovalInstanceResponse.model_validate(instance)


@router.post("/{instance_id}/withdraw", summary="撤回")
async def withdraw_instance(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    account=Depends(require_permission("approval:read")),
):
    service = ApprovalInstanceService(db)
    try:
        instance = await service.withdraw(instance_id, account.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return ApprovalInstanceResponse.model_validate(instance)
