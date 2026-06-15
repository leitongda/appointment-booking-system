"""订阅计划管理路由

包含：
- GET /plans — 获取订阅计划列表
- POST /plans — 创建订阅计划
- GET /plans/{plan_id} — 获取订阅计划详情
- PUT /plans/{plan_id} — 更新订阅计划
- DELETE /plans/{plan_id} — 删除订阅计划
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_current_admin, require_platform_admin
from app.db.session import get_db
from app.modules.tenants.schemas import (
    SubscriptionPlanCreate,
    SubscriptionPlanListResponse,
    SubscriptionPlanResponse,
    SubscriptionPlanUpdate,
)
from app.modules.tenants.service import SubscriptionPlanService

router = APIRouter()


@router.get(
    "/plans",
    response_model=list[SubscriptionPlanListResponse],
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
    status: int | None = Query(None, ge=0, le=1, description="状态筛选: 0-禁用, 1-启用"),
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
