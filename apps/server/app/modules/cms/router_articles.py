"""CMS 文章管理路由"""

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_store_filter, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.models.content_version import ContentVersion
from app.modules.cms.schemas import (
    ArticleCreate,
    ArticleResponse,
    ArticleUpdate,
    BatchDeleteRequest,
)
from app.modules.cms.service import CmsArticleService
from app.schemas.response import PageResponse
from app.utils.audit import get_operator_id_from_admin

router = APIRouter()


def _to_response(article) -> ArticleResponse:
    """序列化文章，还原 tags JSON 文本为列表"""
    payload = {c.name: getattr(article, c.name) for c in article.__table__.columns}
    raw_tags = payload.get("tags")
    if isinstance(raw_tags, str) and raw_tags:
        try:
            payload["tags"] = json.loads(raw_tags)
        except (json.JSONDecodeError, TypeError):
            payload["tags"] = None
    return ArticleResponse.model_validate(payload)


@router.get("", response_model=PageResponse[ArticleResponse], summary="获取文章列表")
async def list_articles(
    site_id: str | None = None,
    category_id: str | None = None,
    article_status: int | None = Query(None, alias="status"),
    keyword: str | None = None,
    store_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(
        require_permission(
            "cms:article", "cms:article:create", "cms:article:update", "cms:article:delete"
        )
    ),
):
    # 非超管按门店过滤：命中门店 或 站点级(store_id 为空)
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter

    service = CmsArticleService(db)
    items, total = await service.get_list(
        tenant_id=current_admin["tenant_id"],
        site_id=site_id,
        category_id=category_id,
        status=article_status,
        keyword=keyword,
        store_id=store_id,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        data=[_to_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/published", response_model=list[ArticleResponse], summary="获取已发布文章（公开）")
async def get_published_articles(
    site_id: str = Query(..., description="站点ID"),
    category_id: str | None = None,
    store_id: str | None = None,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """公开接口，无需鉴权，仅返回已发布文章"""
    service = CmsArticleService(db)
    items = await service.get_published(
        site_id=site_id, category_id=category_id, store_id=store_id, limit=limit
    )
    return [_to_response(item) for item in items]


@router.get("/trash", response_model=PageResponse[ArticleResponse], summary="文章回收站")
async def get_trash_articles(
    site_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:article:delete")),
):
    service = CmsArticleService(db)
    items, total = await service.get_list(
        tenant_id=current_admin["tenant_id"],
        site_id=site_id,
        page=page,
        page_size=page_size,
        deleted_only=True,
    )
    return PageResponse(
        data=[_to_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{article_id}", response_model=ArticleResponse, summary="获取文章详情")
async def get_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:article")),
):
    service = CmsArticleService(db)
    article = await service.get_by_id(article_id)
    if not article or article.tenant_id != current_admin["tenant_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文章不存在，请检查后重试")
    return _to_response(article)


@router.get("/{article_id}/versions", summary="获取文章版本历史")
async def get_article_versions(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:article")),
):
    """获取文章版本历史（先校验文章租户归属，防止按 id 枚举他租户快照）"""
    article = await CmsArticleService(db).get_by_id(article_id)
    if not article or article.tenant_id != current_admin["tenant_id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文章不存在，请检查后重试")

    query = (
        select(ContentVersion)
        .where(ContentVersion.content_type == "cms_article", ContentVersion.content_id == article.id)
        .order_by(ContentVersion.created_at.desc())
    )
    result = await db.execute(query)
    versions = result.scalars().all()
    return [
        {
            "id": v.id,
            "contentType": v.content_type,
            "contentId": v.content_id,
            "operatorId": v.operator_id,
            "snapshot": json.loads(v.snapshot) if v.snapshot else {},
            "createdAt": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


@router.post("", response_model=ArticleResponse, summary="创建文章")
async def create_article(
    data: ArticleCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:article:create")),
):
    service = CmsArticleService(db)
    article = await service.create(
        data.model_dump(exclude_unset=True),
        tenant_id=current_admin["tenant_id"],
        operator_id=get_operator_id_from_admin(current_admin),
    )
    return _to_response(article)


@router.put("/{article_id}", response_model=ArticleResponse, summary="更新文章")
async def update_article(
    article_id: str,
    data: ArticleUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:article:update")),
):
    service = CmsArticleService(db)
    article = await service.update(
        article_id,
        data.model_dump(exclude_unset=True),
        operator_id=get_operator_id_from_admin(current_admin),
        tenant_id=current_admin["tenant_id"],
    )
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文章不存在，请检查后重试")
    return _to_response(article)


@router.delete("/{article_id}", summary="删除文章（移入回收站）")
async def delete_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:article:delete")),
):
    service = CmsArticleService(db)
    success = await service.delete(article_id, tenant_id=current_admin["tenant_id"])
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文章不存在，请检查后重试")
    return {"message": "删除成功"}


@router.post("/{article_id}/restore", summary="恢复文章")
async def restore_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:article:delete")),
):
    service = CmsArticleService(db)
    success = await service.restore(article_id, tenant_id=current_admin["tenant_id"])
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文章不存在或未在回收站中")
    return {"message": "恢复成功"}


@router.delete("/{article_id}/permanent", summary="永久删除文章")
async def permanent_delete_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:article:delete")),
):
    service = CmsArticleService(db)
    success = await service.permanent_delete(article_id, tenant_id=current_admin["tenant_id"])
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文章不存在，请检查后重试")
    return {"message": "永久删除成功"}


@router.post("/batch-delete", summary="批量删除文章")
async def batch_delete_articles(
    data: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("cms:article:delete")),
):
    service = CmsArticleService(db)
    deleted_count = await service.batch_delete(data.ids, tenant_id=current_admin["tenant_id"])
    return {"message": f"成功删除 {deleted_count} 篇文章", "deleted_count": deleted_count}


@router.post("/{article_id}/view", summary="增加文章浏览量")
async def increment_view(
    article_id: str,
    db: AsyncSession = Depends(get_db),
):
    """公开接口，无需鉴权"""
    service = CmsArticleService(db)
    await service.increment_view(article_id)
    return {"message": "ok"}
