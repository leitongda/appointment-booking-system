"""低代码模板市场路由。"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.models.lowcode_template import LowCodeTemplate
from app.models.lowcode_template_version import LowCodeTemplateVersion
from app.modules.lowcode.feature_gate import LowCodeFeatureGate
from app.modules.lowcode.template_service import LowCodeTemplateService
from app.schemas.base import BaseSchema
from app.schemas.response import PageResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# 模板专属 Schemas
# ---------------------------------------------------------------------------


class TemplateCreateRequest(BaseSchema):
    """创建模板请求。"""

    source_page_id: str = Field(..., description="来源页面 ID")
    name: str = Field(..., min_length=1, max_length=200, description="模板名称")
    category: str = Field(..., min_length=1, max_length=50, description="模板分类")
    description: Optional[str] = Field(None, max_length=1000, description="模板描述")
    thumbnail_url: Optional[str] = Field(None, description="缩略图 URL")
    tags: Optional[list[str]] = Field(None, description="标签列表")
    is_public: bool = Field(True, description="是否公开到市场")
    is_official: bool = Field(False, description="是否官方（仅平台管理员）")


class TemplateUpdateRequest(BaseSchema):
    """更新模板元数据请求。"""

    name: Optional[str] = Field(None, min_length=1, max_length=200, description="模板名称")
    description: Optional[str] = Field(None, max_length=1000, description="模板描述")
    thumbnail_url: Optional[str] = Field(None, description="缩略图 URL")
    category: Optional[str] = Field(None, min_length=1, max_length=50, description="模板分类")
    tags: Optional[list[str]] = Field(None, description="标签列表")
    is_public: Optional[bool] = Field(None, description="是否公开到市场")


class TemplateResponse(BaseSchema):
    """模板列表/详情响应。"""

    id: str = Field(..., description="模板 ID")
    source_page_id: Optional[str] = Field(None, description="来源页面 ID")
    name: str = Field(..., description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    thumbnail_url: Optional[str] = Field(None, description="缩略图 URL")
    category: str = Field(..., description="模板分类")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    version: str = Field("1.0.0", description="当前版本")
    is_public: bool = Field(True, description="是否公开")
    is_official: bool = Field(False, description="是否官方")
    download_count: int = Field(0, description="下载次数")
    fork_count: int = Field(0, description="Fork 次数")
    like_count: int = Field(0, description="收藏次数")
    schema_data: Optional[dict[str, Any]] = Field(None, description="Schema JSON（仅详情）")
    data_sources: Optional[list[dict[str, Any]]] = Field(None, description="数据源配置（仅详情）")
    author_id: Optional[str] = Field(None, description="创建人 ID")
    author_name: Optional[str] = Field(None, description="创建人名称")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")


class TemplateVersionItem(BaseSchema):
    """模板版本历史项。"""

    id: str = Field(..., description="版本记录 ID")
    version: str = Field(..., description="语义化版本号")
    changelog: Optional[str] = Field(None, description="变更说明")
    status: int = Field(1, description="版本状态: 1草稿 2已发布 3已废弃")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    created_by: Optional[str] = Field(None, description="创建人 ID")


class TemplateVersionListResponse(BaseSchema):
    """模板版本历史列表响应。"""

    current_version: str = Field("1.0.0", description="模板当前版本号")
    versions: list[TemplateVersionItem] = Field(default_factory=list, description="版本列表 (降序)")


class TemplateCreateVersionRequest(BaseSchema):
    """创建模板新版本请求。"""

    version: str = Field(..., min_length=1, max_length=20, description="语义化版本号，如 1.1.0")
    schema_data: dict[str, Any] = Field(..., description="版本 schema 快照")
    changelog: Optional[str] = Field(None, max_length=500, description="变更说明")
    data_sources: Optional[dict[str, Any]] = Field(None, description="数据源配置快照")


class TemplateCategoryItem(BaseSchema):
    """模板分类项。"""

    name: str = Field(..., description="分类名称")
    count: int = Field(0, description="该分类下模板数量")


class ForkRequest(BaseSchema):
    """Fork 模板请求体。"""

    name: Optional[str] = Field(None, description="新页面名称, 默认为模板名 + (Fork)")
    slug: Optional[str] = Field(None, description="新页面路径, 默认自动生成")


class ForkResponse(BaseSchema):
    """Fork 结果响应。"""

    page_id: str = Field(..., description="Fork 生成的页面 ID")
    message: str = Field("Fork 成功", description="操作结果")


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _get_tenant_id(admin) -> str:
    """安全提取 tenant_id，缺失时抛出 400 错误。"""
    tenant_id = getattr(admin, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="租户信息缺失",
        )
    return str(tenant_id)


def _template_to_response(data: dict[str, Any]) -> TemplateResponse:
    """将 service 返回的 dict 转为 TemplateResponse。"""
    return TemplateResponse(**data)


# ---------------------------------------------------------------------------
# 预定义分类列表
# ---------------------------------------------------------------------------

_TEMPLATE_CATEGORIES = [
    "预约挂号",
    "临时挂号",
    "问诊",
    "健康档案",
    "报告查询",
    "排队叫号",
    "科室导航",
    "健康宣教",
    "满意度调查",
    "公告通知",
    "表单收集",
    "落地页",
    "其他",
]


# ---------------------------------------------------------------------------
# 1. GET /templates -- 市场列表 (公开, 分页, 可筛选)
# ---------------------------------------------------------------------------


@router.get(
    "/templates",
    response_model=PageResponse[TemplateResponse],
    summary="获取模板市场列表",
)
async def get_template_list(
    category: Optional[str] = Query(None, description="分类筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索 (名称/描述)"),
    sort_by: str = Query("popular", description="排序: popular / newest / forks"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
):
    """公开接口，无需认证即可浏览市场。"""
    service = LowCodeTemplateService(db)
    items, total = await service.list_templates(
        category=category,
        keyword=keyword,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        data=[_template_to_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# 2. GET /templates/{template_id} -- 模板详情
# ---------------------------------------------------------------------------


@router.get(
    "/templates/{template_id}",
    response_model=TemplateResponse,
    summary="获取模板详情",
)
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
):
    """公开接口，获取单个模板的完整详情。"""
    service = LowCodeTemplateService(db)
    data = await service.get_template(template_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在",
        )
    return _template_to_response(data)


# ---------------------------------------------------------------------------
# 3. POST /templates -- 创建/发布模板
# ---------------------------------------------------------------------------


@router.post(
    "/templates",
    response_model=TemplateResponse,
    summary="创建模板",
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    data: TemplateCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:template", "lowcode:template:create")),
):
    """从已有页面创建模板并发布到市场。"""
    tenant_id = _get_tenant_id(current_admin)

    gate = LowCodeFeatureGate(db)
    await gate.enforce_feature(tenant_id, "lowcode_marketplace")

    service = LowCodeTemplateService(db)
    try:
        template = await service.create_template(
            source_page_id=data.source_page_id,
            tenant_id=tenant_id,
            name=data.name,
            category=data.category,
            description=data.description,
            thumbnail_url=data.thumbnail_url,
            tags=data.tags,
            is_public=data.is_public,
            created_by=str(current_admin.id),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # 平台管理员可以设置 is_official（平台管理员 tenant_id 为 None）
    if data.is_official and not getattr(current_admin, 'tenant_id', None):
        template.is_official = True
        await db.commit()

    # 重新查询以获取完整的作者信息
    result_data = await service.get_template(str(template.id))
    if result_data:
        return _template_to_response(result_data)
    # fallback: 直接返回基本字段
    return TemplateResponse(
        id=str(template.id),
        name=template.name,
        description=template.description,
        thumbnail_url=template.thumbnail_url,
        category=template.category,
        tags=template.tags or [],
        version=template.version,
        is_public=template.is_public,
        is_official=template.is_official,
        download_count=template.download_count,
        fork_count=template.fork_count,
        like_count=template.like_count,
        created_at=template.created_at,
    )


# ---------------------------------------------------------------------------
# 4. PUT /templates/{template_id} -- 更新元数据
# ---------------------------------------------------------------------------


@router.put(
    "/templates/{template_id}",
    response_model=TemplateResponse,
    summary="更新模板元数据",
)
async def update_template(
    template_id: str,
    data: TemplateUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:template", "lowcode:template:update")),
):
    """更新模板的名称、描述、分类等元数据（不修改 schema）。"""
    tenant_id = _get_tenant_id(current_admin)

    service = LowCodeTemplateService(db)
    template = await service.update_template(
        template_id=template_id,
        name=data.name,
        description=data.description,
        thumbnail_url=data.thumbnail_url,
        category=data.category,
        tags=data.tags,
        is_public=data.is_public,
        updated_by=str(current_admin.id),
    )
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在",
        )

    result_data = await service.get_template(template_id)
    if result_data:
        return _template_to_response(result_data)
    return TemplateResponse(
        id=str(template.id),
        name=template.name,
        description=template.description,
        thumbnail_url=template.thumbnail_url,
        category=template.category,
        tags=template.tags or [],
        version=template.version,
        is_public=template.is_public,
        is_official=template.is_official,
        download_count=template.download_count,
        fork_count=template.fork_count,
        like_count=template.like_count,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


# ---------------------------------------------------------------------------
# 5. DELETE /templates/{template_id} -- 软删除
# ---------------------------------------------------------------------------


@router.delete(
    "/templates/{template_id}",
    summary="删除模板",
)
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:template", "lowcode:template:delete")),
):
    """软删除模板（标记 status=0）。"""
    tenant_id = _get_tenant_id(current_admin)
    service = LowCodeTemplateService(db)
    deleted = await service.delete_template(template_id, tenant_id=tenant_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在",
        )
    return {"message": "删除成功"}


# ---------------------------------------------------------------------------
# 6. POST /templates/{template_id}/fork -- Fork 到当前租户
# ---------------------------------------------------------------------------


@router.post(
    "/templates/{template_id}/fork",
    response_model=ForkResponse,
    summary="Fork 模板到当前租户",
)
async def fork_template(
    template_id: str,
    body: ForkRequest = ForkRequest(),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:template", "lowcode:template:fork")),
):
    """基于模板 schema 在当前租户创建新页面。"""
    tenant_id = _get_tenant_id(current_admin)

    gate = LowCodeFeatureGate(db)
    await gate.enforce_feature(tenant_id, "lowcode_basic")

    service = LowCodeTemplateService(db)
    try:
        page = await service.fork_template(
            template_id=template_id,
            tenant_id=tenant_id,
            account_id=str(current_admin.id),
            name=body.name,
            slug=body.slug,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return ForkResponse(
        page_id=str(page.id),
        message="Fork 成功",
    )


# ---------------------------------------------------------------------------
# 7. GET /templates/{template_id}/versions -- 版本历史
# ---------------------------------------------------------------------------


@router.get(
    "/templates/{template_id}/versions",
    response_model=TemplateVersionListResponse,
    summary="获取模板版本历史",
)
async def list_template_versions(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:template", "lowcode:template:read")),
):
    """按版本号降序列出模板的所有版本记录。"""
    service = LowCodeTemplateService(db)

    # 校验模板存在
    template_data = await service.get_template(template_id)
    if not template_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在",
        )

    versions = await service.get_template_versions(template_id)
    return TemplateVersionListResponse(
        current_version=template_data.get("version", "1.0.0"),
        versions=[
            TemplateVersionItem(
                id=str(v.id),
                version=v.version,
                changelog=v.changelog,
                status=v.status,
                created_at=v.created_at,
                created_by=str(v.created_by) if v.created_by else None,
            )
            for v in versions
        ],
    )


# ---------------------------------------------------------------------------
# 8. POST /templates/{template_id}/versions -- 创建新版本
# ---------------------------------------------------------------------------


@router.post(
    "/templates/{template_id}/versions",
    response_model=TemplateVersionItem,
    summary="创建模板新版本",
    status_code=status.HTTP_201_CREATED,
)
async def create_template_version(
    template_id: str,
    data: TemplateCreateVersionRequest,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:template", "lowcode:template:update")),
):
    """为模板创建新版本快照，同时更新模板主版本号。"""
    service = LowCodeTemplateService(db)
    try:
        version_record = await service.create_version(
            template_id=template_id,
            version=data.version,
            schema_data=data.schema_data,
            changelog=data.changelog,
            data_sources=data.data_sources,
            created_by=str(current_admin.id),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return TemplateVersionItem(
        id=str(version_record.id),
        version=version_record.version,
        changelog=version_record.changelog,
        status=version_record.status,
        created_at=version_record.created_at,
        created_by=str(version_record.created_by) if version_record.created_by else None,
    )


# ---------------------------------------------------------------------------
# 9. GET /templates/my -- 我发布的模板
# ---------------------------------------------------------------------------


@router.get(
    "/templates/my",
    response_model=PageResponse[TemplateResponse],
    summary="获取我发布的模板",
)
async def get_my_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("lowcode:template", "lowcode:template:list")),
):
    """列出当前租户发布的所有模板（含已下架）。"""
    tenant_id = _get_tenant_id(current_admin)

    service = LowCodeTemplateService(db)
    items, total = await service.get_my_templates(
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
    )

    return PageResponse(
        data=[
            TemplateResponse(
                id=str(t.id),
                source_page_id=str(t.source_page_id) if t.source_page_id else None,
                name=t.name,
                description=t.description,
                thumbnail_url=t.thumbnail_url,
                category=t.category,
                tags=t.tags or [],
                version=t.version,
                is_public=t.is_public,
                is_official=t.is_official,
                download_count=t.download_count,
                fork_count=t.fork_count,
                like_count=t.like_count,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# 10. GET /templates/categories -- 分类列表
# ---------------------------------------------------------------------------


@router.get(
    "/templates/categories",
    response_model=list[TemplateCategoryItem],
    summary="获取模板分类列表",
)
async def get_template_categories(
    db: AsyncSession = Depends(get_db),
):
    """返回预定义分类列表及各分类下的模板数量。"""
    # 统计各分类的模板数量
    count_q = (
        select(
            LowCodeTemplate.category,
            func.count(LowCodeTemplate.id).label("count"),
        )
        .where(
            LowCodeTemplate.is_public == True,  # noqa: E712
            LowCodeTemplate.status == 1,
        )
        .group_by(LowCodeTemplate.category)
    )
    result = await db.execute(count_q)
    db_counts = {row[0]: row[1] for row in result.all()}

    # 以预定义分类为基础，合并数据库实际数量
    categories = [
        TemplateCategoryItem(name=cat, count=db_counts.get(cat, 0))
        for cat in _TEMPLATE_CATEGORIES
    ]

    # 补充数据库中存在但预定义列表中没有的分类
    for cat_name, cat_count in db_counts.items():
        if cat_name and cat_name not in _TEMPLATE_CATEGORIES:
            categories.append(TemplateCategoryItem(name=cat_name, count=cat_count))

    return categories
