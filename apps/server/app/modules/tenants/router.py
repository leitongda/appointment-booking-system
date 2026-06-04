"""租户管理路由（组装文件）

将路由拆分为子模块后，本文件仅负责组装和保留未拆分的端点。

子模块：
- router_current_tenant  — 租户自助注册 + /me/* 端点
- router_plans           — 订阅计划 CRUD
- router_migration       — 跨租户数据迁移
- router_usage           — 用量统计 + 订阅记录

本文件保留的端点：
- /tags — 租户标签管理
- /check-unique — 租户标识唯一性检查
- /{tenant_id} CRUD — 租户增删改查
- /{tenant_id}/activate, /suspend — 租户状态管理
- /{tenant_id}/password-policy — 密码策略管理
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import (
    get_current_admin,
    require_platform_admin,
)
from app.db.session import get_db
from app.models.tenant import Tenant
from app.modules.tenants.schemas import (
    PasswordPolicy,
    SubscriptionPlanListResponse,
    TenantCreate,
    TenantListResponse,
    TenantQuery,
    TenantResponse,
    TenantSelfUpdateRequest,
    TenantTagsUpdate,
    TenantUpdate,
)
from app.modules.tenants.service import TenantService
from app.schemas.response import PageResponse

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# ==================== 注册子路由 ====================

from app.modules.tenants.router_current_tenant import (
    router as current_tenant_router,
)
from app.modules.tenants.router_plans import router as plans_router
from app.modules.tenants.router_migration import router as migration_router
from app.modules.tenants.router_usage import router as usage_router

router.include_router(current_tenant_router)
router.include_router(plans_router)
router.include_router(migration_router)
router.include_router(usage_router)


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

    平台管理员可以更新所有租户（使用 TenantUpdate schema）。
    租户管理员只能更新自己的租户且仅限部分字段（使用 TenantSelfUpdateRequest schema）。
    """
    service = TenantService(db)
    tenant = await service.get_by_id(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="租户不存在"
        )

    # 权限检查 + 角色路由：租户管理员使用独立 schema 做类型级字段隔离
    is_platform_admin = current_admin.get("is_super_admin")
    if not is_platform_admin:
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权修改此租户"
            )
        # 仅保留 TenantSelfUpdateRequest 允许的字段，多余字段静默丢弃
        update_data = data.model_dump(exclude_unset=True)
        allowed = set(TenantSelfUpdateRequest.model_fields.keys())
        filtered = {k: v for k, v in update_data.items() if k in allowed}
        data = TenantSelfUpdateRequest(**filtered)

    try:
        tenant = await service.update(tenant_id, data, updated_by=current_admin.get("id"))

        # 同步限流配置到 Redis 缓存（仅平台管理员可修改）
        if is_platform_admin:
            update_fields = data.model_dump(exclude_unset=True)
            if "rate_limit_per_minute" in update_fields or "rate_limit_per_second" in update_fields:
                from app.middleware.rate_limit import RateLimitMiddleware
                await RateLimitMiddleware.cache_tenant_limits(
                    tenant_id,
                    tenant.rate_limit_per_minute,
                    tenant.rate_limit_per_second,
                )

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
        # 清除限流缓存
        from app.middleware.rate_limit import RateLimitMiddleware
        await RateLimitMiddleware.invalidate_tenant_limits(tenant_id)
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
