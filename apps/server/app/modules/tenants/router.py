"""租户管理路由"""
import time
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional, List

from app.db.session import get_db
from app.common.deps import (
    get_current_admin, require_permission, get_platform_admin,
    require_platform_admin,
)
from app.middleware.tenant_context import get_current_tenant_id
from app.models.tenant import Tenant
from app.modules.tenants.schemas import (
    TenantCreate, TenantUpdate, TenantResponse, TenantListResponse, TenantQuery,
    TenantSubscriptionCreate, TenantSubscriptionResponse,
    TenantUsageResponse, TenantUsageSummary, TenantUsageQuery, TenantUsageTrends,
    SubscriptionPlanCreate, SubscriptionPlanUpdate, SubscriptionPlanResponse, SubscriptionPlanListResponse,
    CurrentTenantResponse, CurrentTenantPublicResponse,
    TenantNotificationResponse, TenantNotificationListResponse,
    TenantMigrateRequest, TenantMigrateResponse,
    TenantMigratePrecheckRequest, TenantMigratePrecheckResponse,
    TenantDashboardResponse, TenantSelfRegisterRequest, TenantSelfRegisterResponse,
    PasswordPolicy, TenantTagsUpdate,
)
from app.modules.tenants.service import (
    TenantService, TenantSubscriptionService, TenantUsageService,
    SubscriptionPlanService, TenantNotificationService,
)
from app.schemas.response import PageResponse
from app.core.config import settings

import logging

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
    """
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


# ==================== 租户标签管理 ====================

@router.get("/tags", summary="获取所有租户标签")
async def get_all_tenant_tags(
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin()),
):
    """获取平台下所有租户使用过的标签（去重）"""
    import json as _json

    result = await db.execute(
        select(Tenant.tags).where(
            Tenant.tags != None,
            Tenant.deleted_at.is_(None),
        )
    )
    all_tags = set()
    for (tags_json,) in result.all():
        if tags_json:
            try:
                tags = _json.loads(tags_json)
                if isinstance(tags, list):
                    all_tags.update(t for t in tags if isinstance(t, str))
            except (_json.JSONDecodeError, TypeError):
                pass

    return {"tags": sorted(all_tags)}


@router.put("/{tenant_id}/tags", summary="更新租户标签")
async def update_tenant_tags(
    tenant_id: str,
    data: TenantTagsUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin()),
):
    """更新租户标签（仅平台管理员）"""
    import json as _json

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="租户不存在")

    tenant.tags = _json.dumps(data.tags, ensure_ascii=False)
    tenant.updated_by = current_admin.get("id")
    await db.commit()
    return {"tenant_id": tenant_id, "tags": data.tags}


# ==================== 订阅计划管理（平台管理员） ====================

@router.get(
    "/plans",
    response_model=List[SubscriptionPlanListResponse],
    summary="获取订阅计划列表",
    description="""获取所有可用的订阅计划列表，包括计划名称、价格、配额限制等信息。

**功能说明：**
- 支持按状态筛选（启用/禁用）
- 返回计划列表按排序字段排序
- 包含价格信息和功能配额

**权限要求：**
- 所有管理员都可以查看订阅计划列表

**返回示例：**
```json
[
  {
    "id": "plan_123",
    "plan_code": "basic",
    "name": "基础版",
    "description": "适合小型诊所",
    "price_monthly": 299.00,
    "price_yearly": 2990.00,
    "max_stores": 1,
    "max_doctors": 10,
    "max_appointments_per_month": 500
  }
]
```
"""
)
async def get_subscription_plans(
    status: Optional[int] = Query(None, ge=0, le=1, description="状态筛选: 0-禁用, 1-启用"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取订阅计划列表

    所有管理员都可以查看订阅计划列表。
    """
    service = SubscriptionPlanService(db)
    plans = await service.get_list(status)
    return [SubscriptionPlanListResponse.model_validate(p) for p in plans]


@router.post(
    "/plans",
    response_model=SubscriptionPlanResponse,
    summary="创建订阅计划",
    description="""创建新的订阅计划，仅限平台管理员操作。

**功能说明：**
- 创建新的订阅计划，设置价格和配额限制
- 计划编码必须唯一
- 支持设置月付和年付价格
- 可配置功能开关和配额限制

**权限要求：**
- 仅平台管理员可操作

**请求示例：**
```json
{
  "plan_code": "premium",
  "name": "高级版",
  "description": "适合中型医院",
  "price_monthly": 999.00,
  "price_yearly": 9990.00,
  "max_stores": 5,
  "max_admins": 20,
  "max_doctors": 100,
  "max_appointments_per_month": 5000,
  "features": {"online_payment": true, "wechat_integration": true}
}
```

**错误响应：**
- 400: 计划编码已存在
"""
)
async def create_subscription_plan(
    data: SubscriptionPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin())
):
    """创建订阅计划（仅平台管理员）"""
    service = SubscriptionPlanService(db)

    try:
        plan = await service.create(data)
        return SubscriptionPlanResponse.model_validate(plan)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/plans/{plan_id}", response_model=SubscriptionPlanResponse, summary="获取订阅计划详情")
async def get_subscription_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取订阅计划详情"""
    service = SubscriptionPlanService(db)
    plan = await service.get_by_id(plan_id)

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订阅计划不存在"
        )

    return SubscriptionPlanResponse.model_validate(plan)


@router.put("/plans/{plan_id}", response_model=SubscriptionPlanResponse, summary="更新订阅计划")
async def update_subscription_plan(
    plan_id: str,
    data: SubscriptionPlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin())
):
    """更新订阅计划（仅平台管理员）"""
    service = SubscriptionPlanService(db)

    try:
        plan = await service.update(plan_id, data)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="订阅计划不存在"
            )
        return SubscriptionPlanResponse.model_validate(plan)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/plans/{plan_id}", summary="删除订阅计划")
async def delete_subscription_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin())
):
    """删除订阅计划（仅平台管理员）"""
    service = SubscriptionPlanService(db)

    try:
        success = await service.delete(plan_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="订阅计划不存在"
            )
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== 租户管理（平台管理员） ====================

@router.get("", response_model=PageResponse[TenantListResponse], summary="获取租户列表")
async def get_tenants(
    keyword: Optional[str] = None,
    status: Optional[int] = Query(None, ge=0, le=3, description="状态: 0-禁用 1-正常 2-欠费 3-试用"),
    subscription_plan_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin())
):
    """获取租户列表（仅平台管理员）"""
    service = TenantService(db)
    query = TenantQuery(
        keyword=keyword,
        status=status,
        subscription_plan_id=subscription_plan_id,
        page=page,
        page_size=page_size
    )

    tenants, total = await service.get_list(query)

    # 批量获取门店数和管理员数，避免 N+1 查询
    tenant_ids = [t.id for t in tenants]
    store_counts = await service.get_store_counts_batch(tenant_ids)
    admin_counts = await service.get_admin_counts_batch(tenant_ids)

    # 转换为列表响应
    result = []
    for tenant in tenants:
        store_count = store_counts.get(tenant.id, 0)
        admin_count = admin_counts.get(tenant.id, 0)

        result.append(TenantListResponse(
            id=tenant.id,
            tenant_code=tenant.tenant_code,
            name=tenant.name,
            status=tenant.status,
            subscription_plan_id=tenant.subscription_plan_id,
            subscription_plan_name=tenant.subscription_plan.name if tenant.subscription_plan else None,
            subscription_end_at=tenant.subscription_end_at,
            store_count=store_count,
            admin_count=admin_count,
            created_at=tenant.created_at,
        ))

    return PageResponse(
        data=result,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post(
    "",
    response_model=TenantResponse,
    summary="创建租户",
    description="""创建新的租户（医院/诊所），仅限平台管理员操作。

**功能说明：**
- 创建新的租户账号
- 分配订阅计划和配额
- 设置联系信息和域名
- 初始化租户配置

**请求示例：**
```json
{
  "tenant_code": "hospital_001",
  "name": "示例医院",
  "subscription_plan_id": "plan_basic",
  "billing_cycle": "yearly",
  "max_stores": 3,
  "max_admins": 10,
  "max_doctors": 50,
  "is_trial": false,
  "contact_name": "张经理",
  "contact_phone": "13800138000",
  "contact_email": "manager@hospital.com",
  "address": "北京市朝阳区",
  "custom_domain": "hospital.example.com",
  "subdomain": "hospital"
}
```

**响应示例：**
```json
{
  "id": "tenant_123",
  "tenant_code": "hospital_001",
  "name": "示例医院",
  "status": 1,
  "subscription_plan_id": "plan_basic",
  "subscription_end_at": "2025-01-15T10:30:00Z",
  "max_stores": 3,
  "max_admins": 10,
  "max_doctors": 50,
  "is_subscription_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**错误响应：**
- 400: 租户编码已存在或订阅计划不存在

**权限要求：**
- 仅平台管理员可操作

**多租户说明：**
- tenant_code 必须全局唯一
- 用于子域名或路由识别
- 创建后无法修改
"""
)
async def create_tenant(
    data: TenantCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin())
):
    """创建租户（仅平台管理员）"""
    service = TenantService(db)

    try:
        tenant = await service.create(data, created_by=current_admin.get("id"))
        resp = TenantResponse.model_validate(tenant)
        resp.subscription_plan = SubscriptionPlanListResponse.model_validate(tenant.subscription_plan) if tenant.subscription_plan else None
        return resp
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/check-unique", summary="检查租户标识唯一性")
async def check_tenant_code_unique(
    tenant_code: str = Query(..., min_length=3, max_length=50, description="租户标识"),
    exclude_id: Optional[str] = Query(None, description="排除的租户ID"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """检查租户标识是否已存在"""
    service = TenantService(db)
    exists = await service.check_code_exists(tenant_code, exclude_id)
    return {"exists": exists}


@router.get("/{tenant_id}", response_model=TenantResponse, summary="获取租户详情")
async def get_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取租户详情

    平台管理员可以查看所有租户。
    租户管理员只能查看自己的租户。
    """
    service = TenantService(db)
    tenant = await service.get_by_id(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="租户不存在"
        )

    # 权限检查：非平台管理员只能查看自己的租户
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权访问此租户"
            )

    resp = TenantResponse.model_validate(tenant)
    resp.subscription_plan = SubscriptionPlanListResponse.model_validate(tenant.subscription_plan) if tenant.subscription_plan else None
    return resp


@router.put("/{tenant_id}", response_model=TenantResponse, summary="更新租户")
async def update_tenant(
    tenant_id: str,
    data: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """更新租户

    平台管理员可以更新所有租户。
    租户管理员只能更新自己的租户（部分字段）。
    """
    service = TenantService(db)
    tenant = await service.get_by_id(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="租户不存在"
        )

    # 权限检查
    is_platform_admin = current_admin.get("is_super_admin")
    if not is_platform_admin:
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权修改此租户"
            )
        # 租户管理员只能修改部分字段
        allowed_fields = {"name", "contact_name", "contact_phone", "contact_email", "address", "branding_config"}
        update_data = data.model_dump(exclude_unset=True)
        for field in list(update_data.keys()):
            if field not in allowed_fields:
                del update_data[field]
        data = TenantUpdate(**update_data)

    try:
        tenant = await service.update(tenant_id, data, updated_by=current_admin.get("id"))
        resp = TenantResponse.model_validate(tenant)
        resp.subscription_plan = SubscriptionPlanListResponse.model_validate(tenant.subscription_plan) if tenant.subscription_plan else None
        return resp
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{tenant_id}", summary="删除租户")
async def delete_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin())
):
    """删除租户（仅平台管理员）"""
    service = TenantService(db)

    try:
        success = await service.delete(tenant_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="租户不存在"
            )
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{tenant_id}/activate", summary="激活租户")
async def activate_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin())
):
    """激活租户（仅平台管理员）"""
    service = TenantService(db)
    tenant = await service.activate(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="租户不存在"
        )

    return {"message": "租户已激活"}


@router.post("/{tenant_id}/suspend", summary="暂停租户")
async def suspend_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin())
):
    """暂停租户（仅平台管理员）"""
    service = TenantService(db)
    tenant = await service.suspend(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="租户不存在"
        )

    return {"message": "租户已暂停"}


@router.post(
    "/{tenant_id}/migrate/precheck",
    response_model=TenantMigratePrecheckResponse,
    summary="迁移前预检",
)
async def precheck_tenant_migration(
    tenant_id: str,
    data: TenantMigratePrecheckRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin()),
):
    """迁移前预检：检查目标租户配额、源数据量等（仅平台管理员）"""
    service = TenantService(db)
    try:
        result = await service.precheck_migration(
            target_tenant_id=tenant_id,
            source_tenant_id=data.source_tenant_id,
            entity_types=data.entity_types,
        )
        return TenantMigratePrecheckResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{tenant_id}/migrate",
    response_model=TenantMigrateResponse,
    summary="跨租户数据迁移",
    description="""将源租户的配置类数据迁移到目标租户，仅限平台管理员操作。

**支持迁移的实体类型：**
- stores: 门店
- departments: 科室
- doctors: 医生
- schedule_templates: 排班模板
- doctor_booking_settings: 医生预约设置
- booking_notices: 预约须知
- email_templates: 邮件模板
- message_templates: 消息模板
- rest_days: 休息日
- blacklists: 黑名单
- store_visit_type_configs: 门店复诊规则配置
- store_email_recipients: 门店邮件接收人
- consultation_fee_templates: 诊费模板
- rule_sets: 规则组（含 windows、booking_policy、checkin_policy、capacity_policy、shift_types 关联）

**配额检查：**
- 迁移前会自动检查目标租户的门店数和医生数配额是否足够
- 如果配额不足，返回 400 错误

**ID 处理：**
- 默认生成新的 UUID，避免冲突
- 设置 preserve_ids=true 可保留原始 ID（需谨慎使用）

**请求示例：**
```json
{
  "sourceTenantId": "tenant_abc123",
  "preserveIds": false,
  "entityTypes": ["stores", "departments", "doctors"]
}
```

**响应示例：**
```json
{
  "targetTenantId": "tenant_xyz789",
  "sourceTenantId": "tenant_abc123",
  "durationMs": 1250,
  "copied": {
    "stores": 2,
    "departments": 5,
    "doctors": 10
  },
  "failures": []
}
```
""",
)
async def migrate_tenant_data(
    tenant_id: str,
    data: TenantMigrateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin()),
):
    """跨租户数据迁移（仅平台管理员）"""
    service = TenantService(db)

    try:
        result = await service.migrate_data(
            target_tenant_id=tenant_id,
            source_tenant_id=data.source_tenant_id,
            preserve_ids=data.preserve_ids,
            entity_types=data.entity_types,
            created_by=current_admin.get("id"),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"迁移失败: {str(e)}",
        )

    return TenantMigrateResponse(
        target_tenant_id=tenant_id,
        source_tenant_id=data.source_tenant_id,
        duration_ms=result["duration_ms"],
        copied=result["copied"],
        failures=result["failures"],
    )


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
    from datetime import datetime as dt

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


# ==================== 租户密码策略 ====================

@router.get("/{tenant_id}/password-policy", response_model=PasswordPolicy, summary="获取租户密码策略")
async def get_tenant_password_policy_endpoint(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """获取租户密码策略配置

    平台管理员可查看所有租户；租户管理员只能查看本租户。
    """
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权访问此租户的密码策略"
            )

    from app.modules.tenants.password_policy import get_tenant_password_policy
    policy = await get_tenant_password_policy(db, tenant_id)
    return PasswordPolicy(**policy)


@router.put("/{tenant_id}/password-policy", response_model=PasswordPolicy, summary="更新租户密码策略")
async def update_tenant_password_policy_endpoint(
    tenant_id: str,
    data: PasswordPolicy,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """更新租户密码策略配置

    平台管理员可更新所有租户；租户管理员只能更新本租户。
    """
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权修改此租户的密码策略"
            )

    service = TenantService(db)
    tenant = await service.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="租户不存在")

    import json
    tenant.password_policy = json.dumps(data.model_dump(), sort_keys=True, ensure_ascii=False)
    tenant.updated_by = current_admin.get("id")
    await db.commit()
    await db.refresh(tenant)

    from app.modules.tenants.password_policy import get_tenant_password_policy
    policy = await get_tenant_password_policy(db, tenant_id)
    return PasswordPolicy(**policy)
