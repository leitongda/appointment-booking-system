"""租户自助注册 + 当前租户信息路由

包含：
- POST /register — 租户自助注册（公开接口）
- GET /me — 当前租户信息（admin 用）
- GET /me/public — 当前租户公开信息（患者端匿名）
- GET /me/features — 当前租户功能开关
- GET /me/beta-features — 当前租户灰度功能
- GET /me/sessions — 当前租户活跃会话数
- GET /me/notifications — 当前租户通知列表
- POST /me/notifications/{notification_id}/read — 标记通知已读
- POST /me/notifications/read-all — 标记全部通知已读
- GET /me/dashboard — 租户管理员仪表板
"""
import logging
import time
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.deps import get_current_admin
from app.db.session import get_db
from app.models.tenant import Tenant
from app.modules.tenants.schemas import (
    CurrentTenantPublicResponse,
    CurrentTenantResponse,
    TenantDashboardResponse,
    TenantNotificationListResponse,
    TenantNotificationResponse,
    TenantSelfRegisterRequest,
    TenantSelfRegisterResponse,
)
from app.modules.tenants.service import (
    TenantNotificationService,
    TenantService,
    TenantUsageService,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== 注册端点限流依赖 ====================

_REGISTER_RATE_LIMIT = 10  # 每分钟最多 10 次
_REGISTER_RATE_WINDOW = 60  # 时间窗口：60 秒


async def _check_register_rate_limit(request: Request):
    """IP 级注册限流依赖，基于 Redis 滑动窗口"""
    try:
        from app.core.redis import get_redis
        redis = await get_redis()

        forwarded = request.headers.get("X-Forwarded-For")
        client_ip = forwarded.split(",")[0].strip() if forwarded else (
            request.headers.get("X-Real-IP", "").strip()
            or (request.client.host if request.client else "unknown")
        )

        key = f"rate_limit:register:{client_ip}"
        now = time.time()
        window_start = now - _REGISTER_RATE_WINDOW

        pipeline = redis.pipeline()
        pipeline.zremrangebyscore(key, 0, window_start)
        pipeline.zcard(key)
        pipeline.zadd(key, {str(now): now})
        pipeline.expire(key, _REGISTER_RATE_WINDOW + 1)
        results = await pipeline.execute()

        if results[1] >= _REGISTER_RATE_LIMIT:
            logger.warning(f"注册限流触发: ip={client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="注册请求过于频繁，请稍后再试",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"注册限流检查异常: {e}")


# ==================== 租户自助注册（公开） ====================

@router.post("/register", response_model=TenantSelfRegisterResponse, summary="租户自助注册")
async def register_tenant(
    data: TenantSelfRegisterRequest,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(_check_register_rate_limit),
):
    """自助注册租户（公开接口，无需认证）
    注册后自动创建试用租户（14天试用期）并创建管理员账号。
    支持 captcha_token 人机验证（预留接口，对接第三方 captcha 服务后启用）。
    """
    # captcha 校验占位：接入第三方 captcha 服务时在此处添加校验逻辑
    # if data.captcha_token:
    #     verified = await verify_captcha(data.captcha_token)
    #     if not verified:
    #         raise HTTPException(status_code=400, detail="人机验证失败")

    service = TenantService(db)
    try:
        result = await service.register_tenant(data)
        return TenantSelfRegisterResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==================== 当前租户信息（前端消费） ====================

@router.get("/me", response_model=CurrentTenantResponse, summary="获取当前租户信息（admin 用）")
async def get_current_tenant_info(
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取当前登录管理员所属租户的精简信息"""
    tenant_id = current_admin.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号未关联租户")

    result = await db.execute(
        select(Tenant)
        .options(selectinload(Tenant.subscription_plan))
        .where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="租户不存在")

    days_until_expiry = None
    if tenant.subscription_end_at:
        delta = tenant.subscription_end_at - datetime.utcnow()
        days_until_expiry = max(0, delta.days)

    return CurrentTenantResponse(
        id=tenant.id,
        tenant_code=tenant.tenant_code,
        name=tenant.name,
        status=tenant.status,
        subscription_plan_name=tenant.subscription_plan.name if tenant.subscription_plan else None,
        subscription_end_at=tenant.subscription_end_at,
        is_subscription_active=tenant.is_subscription_active,
        days_until_expiry=days_until_expiry,
        billing_cycle=tenant.billing_cycle or "monthly",
        contact_phone=tenant.contact_phone,
    )


@router.get("/me/public", response_model=CurrentTenantPublicResponse, summary="获取当前租户公开信息（患者端匿名）")
async def get_current_tenant_public(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """患者端通过 X-Tenant-ID/Header 获取租户状态（无需登录，不拦截任何 status）"""
    from app.middleware.tenant_context import get_current_tenant_id as _get_tid

    tenant_id = _get_tid() or getattr(request.state, 'tenant_id', None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少租户上下文")

    result = await db.execute(
        select(Tenant).options(selectinload(Tenant.subscription_plan)).where(Tenant.id == tenant_id)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="租户不存在")

    return CurrentTenantPublicResponse(
        status=t.status,
        subscription_end_at=t.subscription_end_at,
        is_subscription_active=t.is_subscription_active,
        name=t.name,
    )


@router.get("/me/features", summary="获取当前租户有效功能开关")
async def get_current_tenant_features(
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """返回当前租户合并后的功能开关（订阅计划 + 租户覆盖）"""
    tenant_id = current_admin.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号未关联租户")

    from app.common.feature_flags import FeatureFlagService
    features = await FeatureFlagService.get_tenant_features(db, tenant_id)
    return {"tenant_id": tenant_id, "features": features}


@router.get("/me/beta-features", summary="获取当前租户灰度功能")
async def get_current_tenant_beta_features(
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """返回当前租户启用的灰度功能列表"""
    tenant_id = current_admin.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号未关联租户")

    from app.common.feature_flags import FeatureFlagService
    beta = await FeatureFlagService.get_beta_features(db, tenant_id)
    return {"tenant_id": tenant_id, "beta_features": beta}


@router.get("/me/sessions", summary="获取当前租户活跃会话数")
async def get_my_active_sessions(
    current_admin: dict = Depends(get_current_admin),
):
    """获取当前租户的活跃会话数"""
    tenant_id = current_admin.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号未关联租户")

    from app.common.session_limiter import SessionLimiter
    count = await SessionLimiter.get_active_count(tenant_id)
    return {"active_sessions": count}


@router.get("/me/notifications", response_model=TenantNotificationListResponse, summary="获取当前租户通知列表")
async def get_my_notifications(
    unread: bool = Query(False, description="仅未读"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取当前租户的通知列表 + 未读数"""
    tenant_id = current_admin.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号未关联租户")

    service = TenantNotificationService(db)
    items, unread_count, total = await service.get_notifications(
        tenant_id, unread_only=unread, page=page, page_size=page_size,
    )
    return TenantNotificationListResponse(
        items=[TenantNotificationResponse.model_validate(n) for n in items],
        unread_count=unread_count,
        total=total,
    )


@router.post("/me/notifications/{notification_id}/read", summary="标记通知已读")
async def mark_notification_read(
    notification_id: str,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """标记单条通知为已读"""
    tenant_id = current_admin.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号未关联租户")

    service = TenantNotificationService(db)
    ok = await service.mark_read(tenant_id, notification_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在")
    return {"message": "已标记为已读"}


@router.post("/me/notifications/read-all", summary="标记全部通知已读")
async def mark_all_notifications_read(
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """标记当前租户的所有通知为已读"""
    tenant_id = current_admin.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号未关联租户")

    service = TenantNotificationService(db)
    count = await service.mark_all_read(tenant_id)
    return {"message": f"已标记 {count} 条通知为已读"}


@router.get("/me/dashboard", response_model=TenantDashboardResponse, summary="租户管理员仪表板")
async def get_tenant_dashboard(
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取当前租户的仪表板数据（配额用量、今日统计、告警）"""
    tenant_id = current_admin.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号未关联租户")

    result = await db.execute(
        select(Tenant).options(selectinload(Tenant.subscription_plan)).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="租户不存在")

    usage_svc = TenantUsageService(db)
    summary = await usage_svc.get_usage_summary(tenant_id)

    today = date.today()
    today_appts = await usage_svc._get_day_appointment_count(tenant_id, today)
    today_users = await usage_svc._get_day_new_user_count(tenant_id, today)
    active_docs = await usage_svc._get_doctor_count(tenant_id)

    alerts = []
    if tenant.subscription_end_at:
        days_left = (tenant.subscription_end_at - datetime.utcnow()).days
        if days_left <= 7:
            alerts.append({"level": "warning", "message": f"订阅将在 {days_left} 天后到期"})
    if summary["store_usage_rate"] >= 80:
        alerts.append({"level": "info", "message": f"门店使用率已达 {summary['store_usage_rate']}%"})
    if summary["doctor_usage_rate"] >= 80:
        alerts.append({"level": "info", "message": f"医生使用率已达 {summary['doctor_usage_rate']}%"})
    if summary["appointment_usage_rate"] >= 80:
        alerts.append({"level": "warning", "message": f"月预约使用率已达 {summary['appointment_usage_rate']}%"})

    days_until_expiry = None
    if tenant.subscription_end_at:
        days_until_expiry = max(0, (tenant.subscription_end_at - datetime.utcnow()).days)

    return TenantDashboardResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        status=tenant.status,
        plan_name=tenant.subscription_plan.name if tenant.subscription_plan else None,
        subscription_end_at=tenant.subscription_end_at,
        is_subscription_active=tenant.is_subscription_active,
        days_until_expiry=days_until_expiry,
        store_usage={"current": summary["current_store_count"], "max": summary["max_stores"], "rate": summary["store_usage_rate"]},
        admin_usage={"current": summary["current_admin_count"], "max": summary["max_admins"], "rate": summary["admin_usage_rate"]},
        doctor_usage={"current": summary["current_doctor_count"], "max": summary["max_doctors"], "rate": summary["doctor_usage_rate"]},
        appointment_usage={"current": summary["current_month_appointments"], "max": summary["max_appointments_per_month"], "rate": summary["appointment_usage_rate"]},
        today_appointments=today_appts,
        today_new_users=today_users,
        active_doctors=active_docs,
        alerts=alerts,
    )
