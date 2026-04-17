"""Content domain router."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_store_filter, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.modules.content.schemas import (
    BannerCreate,
    BannerResponse,
    NewsCreate,
    NewsResponse,
    NoticeCreate,
    NoticeResponse,
)
from app.modules.content.service import BannerService, NewsService, NoticeService
from app.schemas.response import PageResponse

router = APIRouter()


@router.get("/news", response_model=PageResponse[NewsResponse], summary="获取新闻列表")
async def get_news_list(
    type: Optional[int] = None,
    status: Optional[int] = None,
    keyword: Optional[str] = None,
    store_id: Optional[str] = None,
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


@router.get("/news/published", response_model=List[NewsResponse], summary="获取已发布新闻")
async def get_published_news(
    type: Optional[int] = None,
    store_id: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    service = NewsService(db)
    items = await service.get_published(type=type, store_id=store_id, limit=limit)
    return [NewsResponse.model_validate(item) for item in items]


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


@router.delete("/news/{news_id}", summary="删除新闻")
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


@router.get("/notices", response_model=PageResponse[NoticeResponse], summary="获取公告列表")
async def get_notice_list(
    type: Optional[int] = None,
    status: Optional[int] = None,
    keyword: Optional[str] = None,
    store_id: Optional[str] = None,
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


@router.get("/notices/published", response_model=List[NoticeResponse], summary="获取已发布公告")
async def get_published_notices(
    store_id: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    service = NoticeService(db)
    items = await service.get_published(store_id=store_id, limit=limit)
    return [NoticeResponse.model_validate(item) for item in items]


@router.get("/notices/{notice_id}", response_model=NoticeResponse, summary="获取公告详情")
async def get_notice_detail(
    notice_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = NoticeService(db)
    notice = await service.get_by_id(notice_id)
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在，请检查后重试")
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


@router.delete("/notices/{notice_id}", summary="删除公告")
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


@router.get("/banners", response_model=PageResponse[BannerResponse], summary="获取轮播图列表")
async def get_banner_list(
    position: Optional[str] = None,
    status: Optional[int] = None,
    store_id: Optional[str] = None,
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


@router.get("/banners/active", response_model=List[BannerResponse], summary="获取启用轮播图")
async def get_active_banners(
    position: str = "home",
    store_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    service = BannerService(db)
    items = await service.get_active(position=position, store_id=store_id)
    return [BannerResponse.model_validate(item) for item in items]


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


@router.delete("/banners/{banner_id}", summary="删除轮播图")
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
