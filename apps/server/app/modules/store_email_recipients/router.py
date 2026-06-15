"""Store email recipients domain router."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_store_filter
from app.core.config import settings
from app.core.events import EVENT_TYPE_LABELS, EventType
from app.db.session import get_db
from app.modules.store_email_recipients.service import StoreEmailRecipientService
from app.schemas.store_email_recipient import (
    StoreEmailRecipientCreate,
    StoreEmailRecipientQuery,
    StoreEmailRecipientResponse,
    StoreEmailRecipientUpdate,
)

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
):
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
):
    service = StoreEmailRecipientService(db)
    recipient = await service.get_by_id(recipient_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="接收人不存在")
    return _to_response(recipient)


@router.post("", summary="创建门店邮件接收人")
async def create_store_email_recipient(
    data: StoreEmailRecipientCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
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
):
    service = StoreEmailRecipientService(db)
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
):
    service = StoreEmailRecipientService(db)
    success = await service.delete(recipient_id)
    if not success:
        raise HTTPException(status_code=404, detail="接收人不存在")
    return {"message": "删除成功"}
