"""租户用量统计与订阅记录路由

包含：
- GET /{tenant_id}/usage — 获取租户用量汇总
- GET /{tenant_id}/usage/logs — 获取租户用量日志
- GET /{tenant_id}/usage/trends — 获取租户用量趋势
- GET /{tenant_id}/subscriptions — 获取租户订阅记录
- POST /{tenant_id}/subscriptions — 创建租户订阅
"""
from datetime import datetime as dt
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_current_admin, require_platform_admin
from app.db.session import get_db
from app.modules.tenants.schemas import (
    TenantSubscriptionCreate,
    TenantSubscriptionResponse,
    TenantUsageResponse,
    TenantUsageSummary,
    TenantUsageTrends,
)
from app.modules.tenants.service import (
    TenantSubscriptionService,
    TenantUsageService,
)

router = APIRouter()


# ==================== 租户用量统计 ====================

@router.get("/{tenant_id}/usage", response_model=TenantUsageSummary, summary="获取租户用量汇总")
async def get_tenant_usage(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取租户用量汇总"""
    # 权限检查
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权访问此租户的用量信息"
            )

    service = TenantUsageService(db)

    try:
        summary = await service.get_usage_summary(tenant_id)
        return TenantUsageSummary(**summary)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{tenant_id}/usage/logs", response_model=List[TenantUsageResponse], summary="获取租户用量日志")
async def get_tenant_usage_logs(
    tenant_id: str,
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    limit: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取租户用量日志"""
    # 权限检查
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权访问此租户的用量信息"
            )

    service = TenantUsageService(db)

    # 解析日期
    start = None
    end = None
    if start_date:
        try:
            start = dt.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="开始日期格式错误，应为 YYYY-MM-DD"
            )
    if end_date:
        try:
            end = dt.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="结束日期格式错误，应为 YYYY-MM-DD"
            )

    logs = await service.get_usage_logs(tenant_id, start, end, limit)
    return [TenantUsageResponse.model_validate(log) for log in logs]


@router.get("/{tenant_id}/usage/trends", response_model=TenantUsageTrends, summary="获取租户用量趋势")
async def get_tenant_usage_trends(
    tenant_id: str,
    period_type: str = Query("week", pattern="^(week|month)$", description="周期类型: week / month"),
    periods: int = Query(8, ge=2, le=24, description="返回周期数"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取租户用量趋势（周/月同比环比）"""
    # 权限检查
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权访问此租户的用量信息"
            )

    service = TenantUsageService(db)
    trends_data = await service.get_usage_trends(tenant_id, period_type=period_type, periods=periods)
    return TenantUsageTrends(**trends_data)


# ==================== 租户订阅管理 ====================

@router.post("/{tenant_id}/subscriptions", response_model=TenantSubscriptionResponse, summary="创建租户订阅")
async def create_tenant_subscription(
    tenant_id: str,
    data: TenantSubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin())
):
    """创建租户订阅（仅平台管理员）"""
    service = TenantSubscriptionService(db)

    try:
        subscription = await service.create_subscription(
            tenant_id, data, created_by=current_admin.get("id")
        )
        return TenantSubscriptionResponse.model_validate(subscription)
    except HTTPException:
        # 降级配额检查抛出的 HTTPException 直接透传
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{tenant_id}/subscriptions", response_model=List[TenantSubscriptionResponse], summary="获取租户订阅记录")
async def get_tenant_subscriptions(
    tenant_id: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取租户订阅记录"""
    # 权限检查
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权访问此租户的订阅记录"
            )

    service = TenantSubscriptionService(db)
    subscriptions = await service.get_tenant_subscriptions(tenant_id, limit)
    return [TenantSubscriptionResponse.model_validate(s) for s in subscriptions]
