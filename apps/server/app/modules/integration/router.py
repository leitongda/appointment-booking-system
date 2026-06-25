"""第三方集成配置 API

管理钉钉 / 企业微信 / 飞书 的租户级凭证、连接测试、账号绑定。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth_deps import get_current_super_admin
from app.db.session import get_db
from app.modules.integration.schemas import (
    IntegrationBindingResponse,
    IntegrationCreate,
    IntegrationResponse,
    IntegrationUpdate,
    TestConnectionResponse,
)
from app.modules.integration.service import IntegrationService

router = APIRouter()


def _mask_secret_ref(ref: str | None) -> str | None:
    """脱敏 secret 引用：仅保留 env: 前缀提示，不暴露完整变量名。"""
    if not ref:
        return None
    if ref.startswith("env:"):
        return "env:****"  # 已配置，但不暴露具体变量名
    return "****" if ref else None


def _to_response(integration) -> IntegrationResponse:
    return IntegrationResponse(
        id=integration.id,
        tenant_id=integration.tenant_id,
        provider=integration.provider,
        name=integration.name,
        app_id=integration.app_id,
        app_secret_ref=_mask_secret_ref(integration.app_secret_ref),
        webhook_url=integration.webhook_url,
        webhook_secret_ref=_mask_secret_ref(integration.webhook_secret_ref),
        extra_config=integration.extra_config,
        status=integration.status,
    )


# ========== 平台列表 ==========
@router.get("/providers", summary="获取支持的平台列表")
async def list_providers(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_super_admin),
):
    """列出所有支持的第三方平台及当前配置状态。"""
    service = IntegrationService(db)
    providers = await service.list_providers()
    return {"data": providers}


# ========== 集成配置 CRUD ==========
@router.get("", summary="获取集成配置列表")
async def list_integrations(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_super_admin),
):
    service = IntegrationService(db)
    items = await service.list_integrations()
    return {"data": [_to_response(i) for i in items]}


@router.get("/{provider}", summary="获取指定平台集成配置")
async def get_integration(
    provider: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_super_admin),
):
    service = IntegrationService(db)
    integration = await service.get_by_provider(provider)
    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="集成配置不存在")
    return {"data": _to_response(integration)}


@router.post("", summary="创建/更新集成配置", status_code=status.HTTP_201_CREATED)
async def upsert_integration(
    data: IntegrationCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_super_admin),
):
    """创建或更新集成配置（按平台 upsert，每租户每平台仅一条）。"""
    service = IntegrationService(db)
    integration = await service.upsert(data)
    await db.commit()
    return {"data": _to_response(integration), "message": "保存成功"}


@router.put("/{provider}", summary="更新集成配置")
async def update_integration(
    provider: str,
    data: IntegrationUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_super_admin),
):
    service = IntegrationService(db)
    integration = await service.update(provider, data)
    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="集成配置不存在")
    await db.commit()
    return {"data": _to_response(integration), "message": "保存成功"}


@router.delete("/{provider}", summary="删除集成配置")
async def delete_integration(
    provider: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_super_admin),
):
    service = IntegrationService(db)
    ok = await service.delete(provider)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="集成配置不存在")
    await db.commit()
    return {"message": "删除成功"}


# ========== 连接测试 ==========
@router.post("/test/{provider}", response_model=TestConnectionResponse, summary="测试平台连接")
async def test_connection(
    provider: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_super_admin),
):
    """测试平台凭证是否有效（尝试获取 access_token）。"""
    service = IntegrationService(db)
    result = await service.test_connection(provider)
    return TestConnectionResponse(**result)


# ========== 账号绑定 ==========
@router.get("/bindings/{provider}", summary="获取平台账号绑定列表")
async def list_bindings(
    provider: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_super_admin),
):
    service = IntegrationService(db)
    bindings = await service.list_bindings(provider)
    return {"data": [IntegrationBindingResponse.model_validate(b, from_attributes=True) for b in bindings]}


@router.delete("/bindings/{provider}/{binding_id}", summary="解除账号绑定")
async def delete_binding(
    provider: str,
    binding_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_super_admin),
):
    from app.models.integration import IntegrationBinding

    result = await db.get(IntegrationBinding, binding_id)
    if not result or result.provider != provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="绑定关系不存在")
    await db.delete(result)
    await db.commit()
    return {"message": "解绑成功"}


# ========== 组织架构同步 ==========
@router.post("/sync/{provider}", summary="手动触发组织架构同步")
async def sync_organization(
    provider: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin),
):
    """手动触发指定平台的组织架构同步（部门 + 成员 + 绑定）。

    异步执行：返回 Celery task_id，前端可轮询状态。
    """
    from app.middleware.tenant_context import get_current_tenant_id
    from app.tasks.integration_sync_task import sync_organization_task

    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少租户上下文")

    store_id = current_admin.get("current_store_id")
    task = sync_organization_task.delay(tenant_id, provider, store_id)
    return {
        "message": f"已触发 {provider} 组织架构同步",
        "task_id": task.id,
        "provider": provider,
    }

