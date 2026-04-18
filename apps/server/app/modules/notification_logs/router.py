from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.api.deps import get_current_admin, require_permission
from app.schemas.notification_log import (
    NotificationLogCreate,
    NotificationLogQuery,
    NotificationLogResponse,
    NotificationLogStats,
    NotificationChannel,
    NotificationStatus,
)
from app.schemas.response import PageResponse
from app.modules.notification_logs.service import NotificationLogService
from app.core.config import settings

router = APIRouter()


@router.get("", response_model=PageResponse[NotificationLogResponse], summary="获取通知日志列表")
async def get_notification_logs(
    channel: Optional[NotificationChannel] = None,
    status: Optional[NotificationStatus] = None,
    message_type: Optional[str] = None,
    user_id: Optional[str] = None,
    store_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:monitoring")),
):
    """获取通知日志列表（管理端）"""
    service = NotificationLogService(db)
    query = NotificationLogQuery(
        channel=channel,
        status=status,
        message_type=message_type,
        user_id=user_id,
        store_id=store_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    logs, total = await service.get_list(query)

    return PageResponse(
        data=[NotificationLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=NotificationLogStats, summary="获取通知统计")
async def get_notification_stats(
    store_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:monitoring")),
):
    """获取通知发送统计"""
    service = NotificationLogService(db)
    return await service.get_stats(store_id=store_id, start_date=start_date, end_date=end_date)


@router.get("/{log_id}", response_model=NotificationLogResponse, summary="获取通知日志详情")
async def get_notification_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:monitoring")),
):
    """获取通知日志详情"""
    service = NotificationLogService(db)
    log = await service.get_by_id(log_id)

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知日志不存在",
        )

    return NotificationLogResponse.model_validate(log)


@router.post("/{log_id}/retry", summary="重试失败的通知")
async def retry_notification(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:monitoring")),
):
    """重试失败的通知（预留接口，实际重试逻辑需要根据具体通道实现）"""
    service = NotificationLogService(db)
    log = await service.get_by_id(log_id)

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知日志不存在",
        )

    if log.status != NotificationStatus.FAILED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能重试失败的通知",
        )

    return {"message": "重试功能待实现，需要根据具体通道集成"}
