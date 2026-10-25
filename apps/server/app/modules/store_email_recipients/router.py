"""Store email recipients domain router."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_store_filter, require_admin_tenant_anchor
from app.core.config import settings
from app.core.events import EVENT_TYPE_LABELS, EventType
from app.db.session import get_db
from app.models.store import Store
from app.modules.store_email_recipients.service import StoreEmailRecipientService
from app.schemas.store_email_recipient import (
    StoreEmailRecipientCreate,
    StoreEmailRecipientQuery,
    StoreEmailRecipientResponse,
    StoreEmailRecipientUpdate,
)


# ---------------------------------------------------------------------------
# p3a8 查询侧租户收口：接收人及其门店必须属于锚点租户
# ---------------------------------------------------------------------------

async def _ensure_store_in_tenant(db: AsyncSession, store_id: str | None, tenant_anchor: str | None) -> None:
    if not store_id or not tenant_anchor:
        return
    store = await db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="门店不存在")
    if store.tenant_id != tenant_anchor:
        raise HTTPException(status_code=403, detail="无权访问其他租户的门店数据")


def _ensure_recipient_in_tenant(recipient, tenant_anchor: str | None) -> None:
    """行级校验：tenant_id 为 NULL 的历史行按其门店归属判定（p3a8 已回填，双保险）。"""
    if not tenant_anchor or recipient is None:
        return
    row_tenant = recipient.tenant_id
    if row_tenant is None and recipient.store is not None:
        row_tenant = recipient.store.tenant_id
    if row_tenant is not None and row_tenant != tenant_anchor:
        raise HTTPException(status_code=403, detail="无权访问其他租户的接收人")


router = APIRouter()


def _to_response(recipient) -> StoreEmailRecipientResponse:
    event_types = []
    if recipient.event_types:
        try:
            event_types = json.loads(recipient.event_types)
        except (json.JSONDecodeError, TypeError):
            pass

    store_name = recipient.store.name if recipient.store else ""
    return StoreEmailRecipientResponse(
        id=recipient.id,
        store_id=recipient.store_id,
        store_name=store_name,
        name=recipient.name,
        email=recipient.email,
        event_types=event_types,
        status=recipient.status,
        created_at=recipient.created_at,
        updated_at=recipient.updated_at,
    )


@router.get("/event-types", summary="获取可用事件类型列表")
async def get_event_types(
    current_admin: dict = Depends(get_current_admin),
):
    return [
        {"value": e.value, "label": EVENT_TYPE_LABELS.get(e.value, e.value)}
        for e in EventType
    ]


@router.get("", summary="获取门店邮件接收人列表")
async def get_store_email_recipients(
    store_id: str | None = Query(None, description="门店ID"),
    keyword: str | None = Query(None, description="关键词搜索"),
    status: int | None = Query(None, description="状态"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    await _ensure_store_in_tenant(db, store_id, tenant_anchor)
    admin_store_filter = get_store_filter(current_admin)
    effective_store_id = admin_store_filter or store_id

    service = StoreEmailRecipientService(db)
    query = StoreEmailRecipientQuery(
        store_id=effective_store_id,
        keyword=keyword,
        status=status,
        page=page,
        page_size=page_size,
    )
    recipients, total = await service.get_list(query)

    return {
        "data": [_to_response(r) for r in recipients],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{recipient_id}", summary="获取门店邮件接收人详情")
async def get_store_email_recipient(
    recipient_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    service = StoreEmailRecipientService(db)
    recipient = await service.get_by_id(recipient_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="接收人不存在")
    _ensure_recipient_in_tenant(recipient, tenant_anchor)
    return _to_response(recipient)


@router.post("", summary="创建门店邮件接收人")
async def create_store_email_recipient(
    data: StoreEmailRecipientCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    await _ensure_store_in_tenant(db, data.store_id, tenant_anchor)
    service = StoreEmailRecipientService(db)
    operator_id = current_admin.get("id") if current_admin else None

    try:
        recipient = await service.create(data, operator_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(recipient)


@router.put("/{recipient_id}", summary="更新门店邮件接收人")
async def update_store_email_recipient(
    recipient_id: str,
    data: StoreEmailRecipientUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    service = StoreEmailRecipientService(db)
    existing = await service.get_by_id(recipient_id)
    if not existing:
        raise HTTPException(status_code=404, detail="接收人不存在")
    _ensure_recipient_in_tenant(existing, tenant_anchor)
    operator_id = current_admin.get("id") if current_admin else None

    recipient = await service.update(recipient_id, data, operator_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="接收人不存在")
    return _to_response(recipient)


@router.delete("/{recipient_id}", summary="删除门店邮件接收人")
async def delete_store_email_recipient(
    recipient_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    service = StoreEmailRecipientService(db)
    existing = await service.get_by_id(recipient_id)
    if not existing:
        raise HTTPException(status_code=404, detail="接收人不存在")
    _ensure_recipient_in_tenant(existing, tenant_anchor)
    success = await service.delete(recipient_id)
    if not success:
        raise HTTPException(status_code=404, detail="接收人不存在")
    return {"message": "删除成功"}
