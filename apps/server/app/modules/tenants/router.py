"""租户管理路由"""
from datetime import datetime
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
    TenantUsageResponse, TenantUsageSummary, TenantUsageQuery,
    SubscriptionPlanCreate, SubscriptionPlanUpdate, SubscriptionPlanResponse, SubscriptionPlanListResponse,
    CurrentTenantResponse, CurrentTenantPublicResponse,
    TenantNotificationResponse, TenantNotificationListResponse,
)
from app.modules.tenants.service import (
    TenantService, TenantSubscriptionService, TenantUsageService,
    SubscriptionPlanService, TenantNotificationService,
)
from app.schemas.response import PageResponse
from app.core.config import settings

router = APIRouter()


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
