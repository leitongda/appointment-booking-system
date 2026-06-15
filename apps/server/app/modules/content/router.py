"""Content domain router."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_store_filter, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.models.content_version import ContentVersion
from app.modules.content.schemas import (
    BannerCreate,
    BannerResponse,
    BannerSortRequest,
    BatchDeleteRequest,
    ContentVersionResponse,
    NewsCreate,
    NewsResponse,
    NoticeCreate,
    NoticeResponse,
)
from app.modules.content.service import BannerService, NewsService, NoticeService
from app.schemas.response import PageResponse

router = APIRouter()


# ==================== 新闻 ====================

@router.get("/news", response_model=PageResponse[NewsResponse], summary="获取新闻列表")
async def get_news_list(
    type: int | None = None,
    status: int | None = None,
    keyword: str | None = None,
    store_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(
        require_permission("content:news", "content:news:create", "content:news:update", "content:news:delete")
    ),
):
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter

    service = NewsService(db)
    items, total = await service.get_list(
        type=type,
        status=status,
        keyword=keyword,
        store_id=store_id,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        data=[NewsResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/news/published", response_model=list[NewsResponse], summary="获取已发布新闻")
async def get_published_news(
    type: int | None = None,
    store_id: str | None = None,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    service = NewsService(db)
    items = await service.get_published(type=type, store_id=store_id, limit=limit)
    return [NewsResponse.model_validate(item) for item in items]


@router.get("/news/trash", response_model=PageResponse[NewsResponse], summary="新闻回收站")
async def get_news_trash(
    store_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("content:news:delete")),
):
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter

    service = NewsService(db)
    items, total = await service.get_trash_list(
        store_id=store_id, page=page, page_size=page_size,
    )
    return PageResponse(
        data=[NewsResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/news/{news_id}", response_model=NewsResponse, summary="获取新闻详情")
async def get_news_detail(
    news_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = NewsService(db)
    news = await service.get_by_id(news_id)
    if not news:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="新闻不存在，请检查后重试")

    await service.increment_view(news_id)
    return NewsResponse.model_validate(news)


@router.post("/news", response_model=NewsResponse, summary="创建新闻")
async def create_news(
    data: NewsCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:news:create")),
):
    store_id = None
    if not current_admin.get("is_super_admin"):
        store_id = current_admin.get("current_store_id") or current_admin.get("store_id")

    service = NewsService(db)
    news = await service.create(data.model_dump(), store_id=store_id)
    return NewsResponse.model_validate(news)


@router.put("/news/{news_id}", response_model=NewsResponse, summary="更新新闻")
async def update_news(
    news_id: str,
    data: NewsCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:news:update")),
):
    service = NewsService(db)
    news = await service.update(news_id, data.model_dump())
    if not news:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="新闻不存在，请检查后重试")
    return NewsResponse.model_validate(news)


@router.delete("/news/{news_id}", summary="删除新闻（移入回收站）")
async def delete_news(
    news_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:news:delete")),
):
    service = NewsService(db)
    success = await service.delete(news_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="新闻不存在，请检查后重试")
    return {"message": "删除成功"}


@router.post("/news/{news_id}/restore", summary="恢复新闻")
async def restore_news(
    news_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:news:delete")),
):
    service = NewsService(db)
    success = await service.restore(news_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="新闻不存在或未在回收站中")
    return {"message": "恢复成功"}


@router.delete("/news/{news_id}/permanent", summary="永久删除新闻")
async def permanent_delete_news(
    news_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:news:delete")),
):
    service = NewsService(db)
    success = await service.permanent_delete(news_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="新闻不存在，请检查后重试")
    return {"message": "永久删除成功"}


@router.post("/news/batch-delete", summary="批量删除新闻")
async def batch_delete_news(
    data: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:news:delete")),
):
    service = NewsService(db)
    deleted_count = await service.batch_delete(data.ids)
    return {"message": f"成功删除 {deleted_count} 条新闻", "deleted_count": deleted_count}


# ==================== 公告 ====================

@router.get("/notices", response_model=PageResponse[NoticeResponse], summary="获取公告列表")
async def get_notice_list(
    type: int | None = None,
    status: int | None = None,
    keyword: str | None = None,
    store_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(
        require_permission(
            "content:notice",
            "content:notice:create",
            "content:notice:update",
            "content:notice:delete",
        )
    ),
):
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter

    service = NoticeService(db)
    items, total = await service.get_list(
        type=type,
        status=status,
        keyword=keyword,
        store_id=store_id,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        data=[NoticeResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/notices/published", response_model=list[NoticeResponse], summary="获取已发布公告")
async def get_published_notices(
    store_id: str | None = None,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    service = NoticeService(db)
    items = await service.get_published(store_id=store_id, limit=limit)
    return [NoticeResponse.model_validate(item) for item in items]


@router.get("/notices/trash", response_model=PageResponse[NoticeResponse], summary="公告回收站")
async def get_notices_trash(
    store_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("content:notice:delete")),
):
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter

    service = NoticeService(db)
    items, total = await service.get_trash_list(
        store_id=store_id, page=page, page_size=page_size,
    )
    return PageResponse(
        data=[NoticeResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/notices/{notice_id}", response_model=NoticeResponse, summary="获取公告详情")
async def get_notice_detail(
    notice_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = NoticeService(db)
    notice = await service.get_by_id(notice_id)
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在，请检查后重试")

    await service.increment_view(notice_id)
    return NoticeResponse.model_validate(notice)


@router.post("/notices", response_model=NoticeResponse, summary="创建公告")
async def create_notice(
    data: NoticeCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:notice:create")),
):
    store_id = None
    if not current_admin.get("is_super_admin"):
        store_id = current_admin.get("current_store_id") or current_admin.get("store_id")

    service = NoticeService(db)
    notice = await service.create(data.model_dump(), store_id=store_id)
    return NoticeResponse.model_validate(notice)


@router.put("/notices/{notice_id}", response_model=NoticeResponse, summary="更新公告")
async def update_notice(
    notice_id: str,
    data: NoticeCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:notice:update")),
):
    service = NoticeService(db)
    notice = await service.update(notice_id, data.model_dump())
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在，请检查后重试")
    return NoticeResponse.model_validate(notice)


@router.delete("/notices/{notice_id}", summary="删除公告（移入回收站）")
async def delete_notice(
    notice_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:notice:delete")),
):
    service = NoticeService(db)
    success = await service.delete(notice_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在，请检查后重试")
    return {"message": "删除成功"}


@router.post("/notices/{notice_id}/restore", summary="恢复公告")
async def restore_notice(
    notice_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:notice:delete")),
):
    service = NoticeService(db)
    success = await service.restore(notice_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在或未在回收站中")
    return {"message": "恢复成功"}


@router.delete("/notices/{notice_id}/permanent", summary="永久删除公告")
async def permanent_delete_notice(
    notice_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:notice:delete")),
):
    service = NoticeService(db)
    success = await service.permanent_delete(notice_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在，请检查后重试")
    return {"message": "永久删除成功"}


@router.post("/notices/batch-delete", summary="批量删除公告")
async def batch_delete_notices(
    data: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:notice:delete")),
):
    service = NoticeService(db)
    deleted_count = await service.batch_delete(data.ids)
    return {"message": f"成功删除 {deleted_count} 条公告", "deleted_count": deleted_count}


# ==================== 轮播图 ====================

@router.get("/banners", response_model=PageResponse[BannerResponse], summary="获取轮播图列表")
async def get_banner_list(
    position: str | None = None,
    status: int | None = None,
    store_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(
        require_permission(
            "content:banner",
            "content:banner:create",
            "content:banner:update",
            "content:banner:delete",
        )
    ),
):
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter

    service = BannerService(db)
    items, total = await service.get_list(
        position=position,
        status=status,
        store_id=store_id,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        data=[BannerResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/banners/active", response_model=list[BannerResponse], summary="获取启用轮播图")
async def get_active_banners(
    position: str = "home",
    store_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    service = BannerService(db)
    items = await service.get_active(position=position, store_id=store_id)
    return [BannerResponse.model_validate(item) for item in items]


@router.get("/banners/trash", response_model=PageResponse[BannerResponse], summary="轮播图回收站")
async def get_banners_trash(
    store_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("content:banner:delete")),
):
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter

    service = BannerService(db)
    items, total = await service.get_trash_list(
        store_id=store_id, page=page, page_size=page_size,
    )
    return PageResponse(
        data=[BannerResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/banners/{banner_id}", response_model=BannerResponse, summary="获取轮播图详情")
async def get_banner_detail(
    banner_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = BannerService(db)
    banner = await service.get_by_id(banner_id)
    if not banner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="轮播图不存在，请检查后重试")
    return BannerResponse.model_validate(banner)


@router.post("/banners", response_model=BannerResponse, summary="创建轮播图")
async def create_banner(
    data: BannerCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:banner:create")),
):
    store_id = None
    if not current_admin.get("is_super_admin"):
        store_id = current_admin.get("current_store_id") or current_admin.get("store_id")

    service = BannerService(db)
    banner = await service.create(data.model_dump(), store_id=store_id)
    return BannerResponse.model_validate(banner)


@router.put("/banners/{banner_id}", response_model=BannerResponse, summary="更新轮播图")
async def update_banner(
    banner_id: str,
    data: BannerCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:banner:update")),
):
    service = BannerService(db)
    banner = await service.update(banner_id, data.model_dump())
    if not banner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="轮播图不存在，请检查后重试")
    return BannerResponse.model_validate(banner)


@router.delete("/banners/{banner_id}", summary="删除轮播图（移入回收站）")
async def delete_banner(
    banner_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:banner:delete")),
):
    service = BannerService(db)
    success = await service.delete(banner_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="轮播图不存在，请检查后重试")
    return {"message": "删除成功"}


@router.post("/banners/{banner_id}/restore", summary="恢复轮播图")
async def restore_banner(
    banner_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:banner:delete")),
):
    service = BannerService(db)
    success = await service.restore(banner_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="轮播图不存在或未在回收站中")
    return {"message": "恢复成功"}


@router.delete("/banners/{banner_id}/permanent", summary="永久删除轮播图")
async def permanent_delete_banner(
    banner_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:banner:delete")),
):
    service = BannerService(db)
    success = await service.permanent_delete(banner_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="轮播图不存在，请检查后重试")
    return {"message": "永久删除成功"}


@router.post("/banners/batch-delete", summary="批量删除轮播图")
async def batch_delete_banners(
    data: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:banner:delete")),
):
    service = BannerService(db)
    deleted_count = await service.batch_delete(data.ids)
    return {"message": f"成功删除 {deleted_count} 条轮播图", "deleted_count": deleted_count}


@router.put("/banners/sort", summary="轮播图拖拽排序")
async def update_banner_sort(
    data: BannerSortRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("content:banner:update")),
):
    service = BannerService(db)
    updated_count = await service.update_sort_order(
        [{"id": item.id, "sort_order": item.sort_order} for item in data.items]
    )
    return {"message": f"成功更新 {updated_count} 条轮播图排序", "updated_count": updated_count}


# ==================== 版本历史 ====================

@router.get("/{content_type}/{content_id}/versions", response_model=list[ContentVersionResponse], summary="获取内容版本历史")
async def get_content_versions(
    content_type: str,
    content_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(
        require_permission("content:news", "content:notice", "content:banner")
    ),
):
    if content_type not in ("news", "notice", "banner"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的内容类型，仅支持 news/notice/banner")

    query = (
        select(ContentVersion)
        .where(
            ContentVersion.content_type == content_type,
            ContentVersion.content_id == content_id,
        )
        .order_by(ContentVersion.created_at.desc())
    )
    result = await db.execute(query)
    versions = result.scalars().all()

    return [
        ContentVersionResponse(
            id=v.id,
            content_type=v.content_type,
            content_id=v.content_id,
            operator_id=v.operator_id,
            snapshot=json.loads(v.snapshot),
            created_at=v.created_at,
        )
        for v in versions
    ]
