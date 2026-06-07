"""低代码页面路由。"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.modules.lowcode.codegen_service import CodegenError, CodegenService
from app.modules.lowcode.schemas import (
    AuditLogItem,
    AuditLogListResponse,
    CodegenPreviewRequest,
    CodegenResultSchema,
    DataSourceTestRequest,
    DataSourceTestResponse,
    DataPreviewResponse,
    DeployResultResponse,
    DeployRollbackRequest,
    DeployRollbackResponse,
    DeployStatusResponse,
    LowCodePageCreate,
    LowCodePageResponse,
    LowCodePageUpdate,
    PreviewDeployResponse,
    RollbackRequest,
    VersionItem,
    VersionListResponse,
    WeChatAuditCallbackRequest,
    WeChatAuditCallbackResponse,
)
from app.modules.lowcode.feature_gate import LowCodeFeatureGate
from app.modules.lowcode.service import LowCodePageService
from app.modules.lowcode.version_service import LowCodePageVersionService
from app.schemas.response import PageResponse

router = APIRouter()


def _get_tenant_id(admin) -> str:
    """安全提取 tenant_id，缺失时抛出 400 错误。"""
    tenant_id = getattr(admin, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="租户信息缺失",
        )
    return str(tenant_id)


def _validate_component_nodes(node: dict, path: str = "root") -> None:
    """递归校验 schema 中每个节点都有 componentName。"""
    if "componentName" not in node:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"节点 '{path}' 缺少 componentName 字段",
        )
    children = node.get("children") or node.get("props", {}).get("children", [])
    if isinstance(children, list):
        for i, child in enumerate(children):
            if isinstance(child, dict):
                _validate_component_nodes(child, path=f"{path}.children[{i}]")


@router.get("/pages", response_model=PageResponse[LowCodePageResponse], summary="获取页面列表")
async def get_page_list(
    status_filter: Optional[int] = Query(None, alias="status", description="状态筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:list")),
):
    tenant_id = _get_tenant_id(current_admin)
    service = LowCodePageService(db)
    items, total = await service.get_list(
        tenant_id=tenant_id,
        status=status_filter,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        data=[LowCodePageResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/pages", response_model=LowCodePageResponse, summary="创建页面")
async def create_page(
    data: LowCodePageCreate,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:create")),
):
    tenant_id = _get_tenant_id(current_admin)

    # 功能门禁：lowcode_basic + 页面配额
    gate = LowCodeFeatureGate(db)
    await gate.enforce_feature(tenant_id, "lowcode_basic")
    await gate.enforce_page_limit(tenant_id)

    service = LowCodePageService(db)

    # 检查 slug 唯一性
    is_unique = await service.check_slug_unique(tenant_id, data.slug)
    if not is_unique:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="页面标识已存在",
        )

    page = await service.create(
        tenant_id=tenant_id,
        name=data.name,
        slug=data.slug,
        description=data.description,
        schema_data=data.schema_data,
        thumbnail_url=data.thumbnail_url,
        miniapp_instance_id=data.miniapp_instance_id,
        created_by=str(current_admin.id),
    )
    return LowCodePageResponse.model_validate(page)


@router.get("/pages/{page_id}", response_model=LowCodePageResponse, summary="获取页面详情")
async def get_page(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:read")),
):
    tenant_id = _get_tenant_id(current_admin)
    service = LowCodePageService(db)
    page = await service.get_by_id(tenant_id, page_id)
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="页面不存在",
        )
    return LowCodePageResponse.model_validate(page)


@router.put("/pages/{page_id}", response_model=LowCodePageResponse, summary="更新页面")
async def update_page(
    page_id: str,
    data: LowCodePageUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:update")),
):
    tenant_id = _get_tenant_id(current_admin)
    service = LowCodePageService(db)

    # 如果更新 slug，检查唯一性
    if data.slug:
        is_unique = await service.check_slug_unique(tenant_id, data.slug, exclude_id=page_id)
        if not is_unique:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="页面标识已存在",
            )

    page = await service.update(
        tenant_id=tenant_id,
        page_id=page_id,
        name=data.name,
        slug=data.slug,
        description=data.description,
        schema_data=data.schema_data,
        status=data.status,
        thumbnail_url=data.thumbnail_url,
        miniapp_instance_id=data.miniapp_instance_id,
        updated_by=str(current_admin.id),
    )
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="页面不存在",
        )
    return LowCodePageResponse.model_validate(page)


@router.delete("/pages/{page_id}", summary="删除页面")
async def delete_page(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:delete")),
):
    tenant_id = _get_tenant_id(current_admin)
    service = LowCodePageService(db)
    deleted = await service.delete(tenant_id, page_id, deleted_by=str(current_admin.id))
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="页面不存在或非草稿状态不可删除",
        )
    return {"message": "删除成功"}


@router.post("/pages/batch-delete", summary="批量删除页面")
async def batch_delete_pages(
    page_ids: list[str],
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:delete")),
):
    """批量删除页面（仅草稿状态可删除）"""
    tenant_id = _get_tenant_id(current_admin)
    service = LowCodePageService(db)
    deleted = 0
    for page_id in page_ids:
        if await service.delete(tenant_id, page_id):
            deleted += 1
    return {"message": f"成功删除 {deleted} 个页面", "deleted": deleted}


@router.post("/pages/batch-status", summary="批量变更页面状态")
async def batch_update_status(
    page_ids: list[str],
    target_status: int,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:update")),
):
    """批量变更页面状态"""
    tenant_id = _get_tenant_id(current_admin)
    service = LowCodePageService(db)
    updated = 0
    for page_id in page_ids:
        page = await service.get(tenant_id, page_id)
        if page:
            page.status = target_status
            await service.update(tenant_id, page_id, {"status": target_status})
            updated += 1
    return {"message": f"成功更新 {updated} 个页面", "updated": updated}


@router.get("/pages/{page_id}/export", summary="导出页面 Schema")
async def export_page(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """导出页面 Schema 为 JSON 文件"""
    import json
    from fastapi.responses import Response

    tenant_id = _get_tenant_id(current_admin)
    service = LowCodePageService(db)
    page = await service.get(tenant_id, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="页面不存在")

    export_data = {
        "schema_data": page.schema_data,
        "tenant_id": str(page.tenant_id),
        "name": page.name,
        "slug": page.slug,
        "description": page.description,
        "exported_at": page.updated_at.isoformat() if page.updated_at else None,
        "version": "1.0",
    }
    content = json.dumps(export_data, ensure_ascii=False, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{page.slug or page_id}.json"'},
    )


@router.post("/pages/import", response_model=LowCodePageResponse, summary="导入页面 Schema")
async def import_page(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:create")),
):
    """从 JSON 文件导入页面"""
    import json

    tenant_id = _get_tenant_id(current_admin)

    # 功能门禁：lowcode_basic + 页面配额
    gate = LowCodeFeatureGate(db)
    await gate.enforce_feature(tenant_id, "lowcode_basic")
    await gate.enforce_page_limit(tenant_id)

    content = await file.read()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的 JSON 文件")

    if "schema_data" not in data:
        raise HTTPException(status_code=400, detail="缺少 schema_data 字段")

    # 如果导入数据包含 tenant_id，校验与当前租户一致
    imported_tenant_id = data.get("tenant_id")
    if imported_tenant_id and str(imported_tenant_id) != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="导入数据的租户标识与当前租户不匹配",
        )

    # 校验 schema_data 基础结构
    schema_data = data["schema_data"]
    if not isinstance(schema_data, dict):
        raise HTTPException(status_code=400, detail="schema_data 必须是 JSON 对象")

    root_component = schema_data.get("componentName")
    if root_component != "Page":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"schema_data 根节点 componentName 必须为 'Page'，实际为 '{root_component}'",
        )

    # 递归检查每个节点都有 componentName
    _validate_component_nodes(schema_data)

    service = LowCodePageService(db)
    # 生成唯一的 slug（添加时间戳后缀避免冲突）
    import time
    base_slug = data.get("slug", "imported")
    slug = f"{base_slug}-{int(time.time())}"

    page = await service.create(
        tenant_id,
        name=data.get("name", "导入的页面"),
        slug=slug,
        description=data.get("description", ""),
        schema_data=data["schema_data"],
        created_by=str(current_admin.id),
    )
    return LowCodePageResponse.model_validate(page)


@router.post("/pages/{page_id}/publish", response_model=LowCodePageResponse, summary="发布页面")
async def publish_page(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:publish")),
):
    tenant_id = _get_tenant_id(current_admin)
    service = LowCodePageService(db)

    # 如果 schema 含 dataBindings，需检查 lowcode_advanced_components
    page = await service.get_by_id(tenant_id, page_id)
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="页面不存在",
        )
    schema_data = getattr(page, "schema_data", None) or {}
    has_data_bindings = isinstance(schema_data, dict) and schema_data.get("dataBindings")
    if has_data_bindings:
        gate = LowCodeFeatureGate(db)
        await gate.enforce_feature(tenant_id, "lowcode_advanced_components")

    page = await service.update(
        tenant_id=tenant_id,
        page_id=page_id,
        status=1,
        updated_by=str(current_admin.id),
    )
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="页面不存在",
        )
    return LowCodePageResponse.model_validate(page)


@router.post("/pages/{page_id}/archive", response_model=LowCodePageResponse, summary="归档页面")
async def archive_page(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:update")),
):
    tenant_id = _get_tenant_id(current_admin)
    service = LowCodePageService(db)
    page = await service.update(
        tenant_id=tenant_id,
        page_id=page_id,
        status=2,
        updated_by=str(current_admin.id),
    )
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="页面不存在",
        )
    return LowCodePageResponse.model_validate(page)


@router.post("/data-sources/test", response_model=DataSourceTestResponse, summary="测试数据源")
async def test_data_source(
    data: DataSourceTestRequest,
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:read")),
):
    """沙箱测试数据源配置。

    限制: 超时 5 秒, 响应体最大 1 MB。
    返回响应样本及字段建议，供设计器绑定使用。
    """
    result = await LowCodePageService.test_data_source(
        url=data.url,
        method=data.method,
        headers=data.headers,
        params=data.params,
        body=data.body,
        response_path=data.response_path,
    )
    return DataSourceTestResponse.model_validate(result)


@router.get("/pages/{page_id}/data-preview", response_model=DataPreviewResponse, summary="页面数据预览")
async def get_page_data_preview(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:read")),
):
    """加载页面 schema，根据 dataSources 配置返回模拟数据结构。

    不实际发起网络请求，仅基于 schema 定义生成 mock 数据，供设计器预览。
    """
    tenant_id = _get_tenant_id(current_admin)
    service = LowCodePageService(db)
    page = await service.get_with_data_sources(tenant_id, page_id)
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="页面不存在",
        )
    preview_items = service.build_data_preview(page)
    return DataPreviewResponse(
        page_id=str(page.id),
        page_name=page.name,
        data_sources=preview_items,
    )


# ---------------------------------------------------------------------------
# Codegen endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/pages/{page_id}/codegen/preview",
    response_model=CodegenResultSchema,
    summary="预览代码生成结果",
)
async def codegen_preview(
    page_id: str,
    data: CodegenPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:read")),
):
    """预览代码生成结果 (不持久化到磁盘)。

    接受前端传入的 schema、数据源配置和目标平台，
    返回生成的源代码文件列表，供前端展示预览。
    """
    tenant_id = _get_tenant_id(current_admin)

    gate = LowCodeFeatureGate(db)
    await gate.enforce_feature(tenant_id, "lowcode_codegen")

    service = CodegenService(db)

    try:
        result = await service.preview_codegen(
            schema=data.schema_data,
            data_sources=data.data_sources,
            target=data.target,
        )
    except CodegenError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return CodegenResultSchema(
        files=[
            {
                "path": f.path,
                "content": f.content,
                "type": f.type.value,
            }
            for f in result.files
        ],
        warnings=result.warnings,
        dependencies=result.dependencies,
        metadata=result.metadata,
    )


@router.post(
    "/pages/{page_id}/codegen/taro",
    response_model=CodegenResultSchema,
    summary="生成 Taro 小程序代码",
)
async def codegen_taro(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:codegen")),
):
    """为指定低代码页面生成 Taro 小程序源代码。

    从数据库加载页面 schema，调用 Node.js codegen 包生成
    .tsx 页面文件，返回生成结果。
    """
    tenant_id = _get_tenant_id(current_admin)

    gate = LowCodeFeatureGate(db)
    await gate.enforce_feature(tenant_id, "lowcode_codegen")

    service = CodegenService(db)

    try:
        result = await service.generate_taro(
            page_id=page_id,
            tenant_id=tenant_id,
        )
    except CodegenError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return CodegenResultSchema(
        files=[
            {
                "path": f.path,
                "content": f.content,
                "type": f.type.value,
            }
            for f in result.files
        ],
        warnings=result.warnings,
        dependencies=result.dependencies,
        metadata=result.metadata,
    )


@router.get(
    "/pages/{page_id}/codegen/download",
    summary="下载生成的代码压缩包",
)
async def codegen_download(
    page_id: str,
    target: str = Query("taro", description="目标平台: taro / native"),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:codegen")),
):
    """下载生成的代码文件 (ZIP 格式)。

    根据 target 参数生成 Taro 或原生小程序代码，
    打包为 ZIP 文件返回下载。
    """
    import io
    import zipfile

    tenant_id = _get_tenant_id(current_admin)

    gate = LowCodeFeatureGate(db)
    await gate.enforce_feature(tenant_id, "lowcode_codegen")

    service = CodegenService(db)

    try:
        if target == "native":
            result = await service.generate_native(
                page_id=page_id,
                tenant_id=tenant_id,
            )
        else:
            result = await service.generate_taro(
                page_id=page_id,
                tenant_id=tenant_id,
            )
    except CodegenError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # 构建 ZIP 文件
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in result.files:
            zf.writestr(f.path, f.content)
    buf.seek(0)

    suffix = "taro" if target != "native" else "native"
    filename = f"lowcode-{page_id}-{suffix}.zip"

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# ---------------------------------------------------------------------------
# Version History
# ---------------------------------------------------------------------------


@router.get(
    "/pages/{page_id}/versions",
    response_model=VersionListResponse,
    summary="获取页面版本历史",
)
async def list_versions(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:read")),
):
    """按版本号降序列出页面的所有版本记录。"""
    tenant_id = _get_tenant_id(current_admin)

    # 校验页面存在
    page_service = LowCodePageService(db)
    page = await page_service.get_by_id(tenant_id, page_id)
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="页面不存在",
        )

    version_service = LowCodePageVersionService(db)
    versions = await version_service.get_versions(page_id, tenant_id)
    return VersionListResponse(
        current_version=page.current_version or 0,
        versions=[
            VersionItem(
                id=str(v.id),
                version=v.version,
                snapshot_label=v.snapshot_label,
                created_at=v.created_at,
                created_by=v.created_by,
            )
            for v in versions
        ],
    )


@router.post(
    "/pages/{page_id}/versions/rollback",
    response_model=LowCodePageResponse,
    summary="回滚到指定版本",
)
async def rollback_version(
    page_id: str,
    data: RollbackRequest,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:update")),
):
    """将页面回滚到指定历史版本。"""
    tenant_id = _get_tenant_id(current_admin)
    version_service = LowCodePageVersionService(db)
    try:
        page = await version_service.rollback_to_version(
            page_id=page_id,
            version_id=data.version_id,
            tenant_id=tenant_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return LowCodePageResponse.model_validate(page)


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------


@router.get(
    "/pages/{page_id}/audit-logs",
    response_model=AuditLogListResponse,
    summary="获取页面审计日志",
)
async def list_audit_logs(
    page_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:read")),
):
    """获取指定页面的操作审计日志，按操作时间降序排列。"""
    tenant_id = _get_tenant_id(current_admin)
    service = LowCodePageService(db)
    logs, total = await service.get_audit_logs(
        page_id=page_id,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
    )
    return AuditLogListResponse(
        items=[
            AuditLogItem(
                id=str(log.id),
                page_id=str(log.page_id),
                operator_id=str(log.operator_id),
                action=log.action,
                detail=log.detail,
                created_at=log.created_at,
            )
            for log in logs
        ],
        total=total,
    )


# ---------------------------------------------------------------------------
# Marketplace & Deploy
# ---------------------------------------------------------------------------


@router.post("/pages/{page_id}/publish-to-marketplace", response_model=LowCodePageResponse, summary="发布到组件市场")
async def publish_to_marketplace(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:publish")),
):
    """将页面发布到组件市场，供其他租户复用。"""
    tenant_id = _get_tenant_id(current_admin)

    gate = LowCodeFeatureGate(db)
    await gate.enforce_feature(tenant_id, "lowcode_marketplace")

    service = LowCodePageService(db)
    page = await service.update(
        tenant_id=tenant_id,
        page_id=page_id,
        status=3,  # 3 = 已上架市场
        updated_by=str(current_admin.id),
    )
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="页面不存在",
        )
    return LowCodePageResponse.model_validate(page)


@router.post(
    "/pages/{page_id}/deploy",
    response_model=DeployResultResponse,
    summary="触发完整部署流水线",
)
async def deploy_page(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:deploy")),
):
    """触发完整部署流水线: 代码生成 -> 构建 -> 上传 -> 微信审核。

    需要 lowcode_publish_miniapp 功能开关。
    页面必须已关联小程序实例。
    """
    from app.modules.lowcode.deploy_service import DeployError, LowCodeDeployService

    tenant_id = _get_tenant_id(current_admin)

    gate = LowCodeFeatureGate(db)
    await gate.enforce_feature(tenant_id, "lowcode_publish_miniapp")

    service = LowCodeDeployService(db)
    try:
        result = await service.trigger_deploy(
            tenant_id=tenant_id,
            page_id=page_id,
            updated_by=str(current_admin.id),
        )
    except DeployError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return DeployResultResponse(**result)


@router.get(
    "/pages/{page_id}/deploy-status",
    response_model=DeployStatusResponse,
    summary="获取部署状态",
)
async def get_deploy_status(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:read")),
):
    """查询页面的当前部署状态，包括部署阶段和最近构建任务信息。

    需要 lowcode_publish_miniapp 功能开关。
    """
    from app.modules.lowcode.deploy_service import DeployError, LowCodeDeployService

    tenant_id = _get_tenant_id(current_admin)

    gate = LowCodeFeatureGate(db)
    await gate.enforce_feature(tenant_id, "lowcode_publish_miniapp")

    service = LowCodeDeployService(db)
    try:
        result = await service.get_deploy_status(
            tenant_id=tenant_id,
            page_id=page_id,
        )
    except DeployError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return DeployStatusResponse(**result)


@router.post(
    "/pages/{page_id}/deploy-rollback",
    response_model=DeployRollbackResponse,
    summary="回滚到上一个已发布版本",
)
async def deploy_rollback(
    page_id: str,
    data: DeployRollbackRequest,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:deploy")),
):
    """将部署回滚到上一个已发布版本。

    需要 lowcode_publish_miniapp 功能开关。
    仅在已发布/审核中/失败状态下允许回滚。
    """
    from app.modules.lowcode.deploy_service import DeployError, LowCodeDeployService

    tenant_id = _get_tenant_id(current_admin)

    gate = LowCodeFeatureGate(db)
    await gate.enforce_feature(tenant_id, "lowcode_publish_miniapp")

    service = LowCodeDeployService(db)
    try:
        result = await service.rollback_deploy(
            tenant_id=tenant_id,
            page_id=page_id,
            target_version=data.target_version,
            updated_by=str(current_admin.id),
        )
    except DeployError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return DeployRollbackResponse(**result)


@router.post(
    "/pages/{page_id}/preview-deploy",
    response_model=PreviewDeployResponse,
    summary="生成预览二维码",
)
async def preview_deploy(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:page", "lowcode:page:deploy")),
):
    """上传代码到微信开发版并生成体验二维码，供测试人员扫码预览。

    需要 lowcode_publish_miniapp 功能开关。
    页面必须已关联小程序实例。
    """
    from app.modules.lowcode.deploy_service import DeployError, LowCodeDeployService

    tenant_id = _get_tenant_id(current_admin)

    gate = LowCodeFeatureGate(db)
    await gate.enforce_feature(tenant_id, "lowcode_publish_miniapp")

    service = LowCodeDeployService(db)
    try:
        result = await service.generate_preview_qr(
            tenant_id=tenant_id,
            page_id=page_id,
        )
    except DeployError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return PreviewDeployResponse(**result)


@router.post(
    "/deploy/wechat-audit-callback",
    response_model=WeChatAuditCallbackResponse,
    summary="微信审核状态回调",
)
async def wechat_audit_callback(
    data: WeChatAuditCallbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """接收微信审核状态更新的 Webhook 回调。

    微信在审核完成后会调用此接口，通知审核结果。
    根据审核结果自动更新部署状态 (published / failed)。

    注意: 此端点为公开回调，不走管理员认证。
    TODO: 接入时需增加微信回调签名校验。
    """
    from app.modules.lowcode.deploy_service import DeployError, LowCodeDeployService

    service = LowCodeDeployService(db)
    try:
        result = await service.handle_audit_callback(
            callback_data=data.model_dump(),
        )
    except DeployError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return WeChatAuditCallbackResponse(**result)
