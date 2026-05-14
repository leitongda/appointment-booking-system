from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.models.notification_log import NotificationLog
from app.api.deps import get_current_admin, require_permission
from app.schemas.notification_log import (
    NotificationLogCreate,
    NotificationLogQuery,
    NotificationLogResponse,
    NotificationLogStats,
    NotificationChannel,
    NotificationStatus,
    NotificationUsageStats,
    NotificationQuotaInfo,
    NotificationQuotaUpdate,
)
from app.schemas.response import PageResponse
from app.modules.notification_logs.service import NotificationLogService
from app.infrastructure.notifications.quota import NotificationQuotaService
from app.core.config import settings
from app.middleware.tenant_context import get_current_tenant_id

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
    """重试失败的通知

    将通知状态重置为待重试，由 Celery 定时任务在下一个周期自动拾取并发送。
    支持 email / sms / wechat 渠道，站内信不支持重试。
    """
    service = NotificationLogService(db)
    log = await service.get_by_id(log_id)

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知日志不存在",
        )

    if log.status not in (NotificationStatus.FAILED.value, NotificationStatus.PERMANENTLY_FAILED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能重试失败的通知",
        )

    if log.channel == "in_app":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="站内信渠道不支持重试",
        )

    # 重置状态，让定时任务立即拾取
    await db.execute(
        update(NotificationLog)
        .where(NotificationLog.id == log_id)
        .values(
            status=NotificationStatus.FAILED.value,
            retry_count=0,
            next_retry_at=datetime.utcnow(),
            error_message=None,
        )
    )
    await db.commit()

    return {"message": "已加入重试队列，将在下一周期自动发送"}


@router.get("/usage-stats", response_model=dict, summary="获取通知用量统计")
async def get_notification_usage_stats(
    period: str = Query("month", description="统计周期: day/week/month"),
    tenant_id: Optional[str] = Query(None, description="租户ID，不传则使用当前租户"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:monitoring")),
):
    """获取通知用量统计"""
    effective_tenant_id = tenant_id or get_current_tenant_id()
    if not effective_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法确定租户ID",
        )

    service = NotificationLogService(db)
    return await service.get_usage_stats(tenant_id=effective_tenant_id, period=period)


@router.get("/quota", response_model=NotificationQuotaInfo, summary="获取通知配额信息")
async def get_notification_quota(
    tenant_id: Optional[str] = Query(None, description="租户ID，不传则使用当前租户"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:monitoring")),
):
    """获取通知配额信息"""
    effective_tenant_id = tenant_id or get_current_tenant_id()
    if not effective_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法确定租户ID",
        )

    quota_service = NotificationQuotaService(db)
    quota_info = await quota_service.get_quota_info(effective_tenant_id)

    return NotificationQuotaInfo(**quota_info)


@router.put("/quota", summary="更新通知配额设置")
async def update_notification_quota(
    quota_update: NotificationQuotaUpdate,
    tenant_id: Optional[str] = Query(None, description="租户ID，不传则使用当前租户"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:config")),
):
    """更新通知配额设置（管理员）

    注意：当前实现将配额存储在 system_settings 中，
    更好的方案是在 Tenant 或 SubscriptionPlan 中添加配额字段。
    """
    effective_tenant_id = tenant_id or get_current_tenant_id()
    if not effective_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法确定租户ID",
        )

    from app.models.settings import SystemSetting

    update_count = 0
    for field, value in quota_update.model_dump(exclude_unset=True).items():
        if value is not None:
            # 检查是否已存在
            result = await db.execute(
                select(SystemSetting).where(
                    SystemSetting.category == "notification_quota",
                    SystemSetting.key == field,
                )
            )
            setting = result.scalar_one_or_none()

            if setting:
                setting.value = str(value)
            else:
                new_setting = SystemSetting(
                    category="notification_quota",
                    key=field,
                    value=str(value),
                    description=f"{field} 配额",
                )
                db.add(new_setting)
            update_count += 1

    await db.commit()

    return {
        "message": f"成功更新 {update_count} 个配额设置",
        "updated_count": update_count,
    }
