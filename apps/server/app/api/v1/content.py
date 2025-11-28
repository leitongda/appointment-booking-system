"""内容管理 API"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.services.content_service import NewsService, NoticeService, BannerService
from app.schemas.response import PageResponse

router = APIRouter()


# ========== Schemas ==========
class NewsCreate(BaseModel):
    title: str = Field(..., max_length=200)
    type: int = Field(1, ge=1, le=4)
    cover_image: Optional[str] = None
    summary: Optional[str] = None
    content: str
    is_top: int = Field(0, ge=0, le=1)
    status: int = Field(0, ge=0, le=1)


class NewsResponse(BaseModel):
    id: str
    title: str
    type: int
    cover_image: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    view_count: int = 0
    is_top: int = 0
    status: int = 0
    publish_time: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NoticeCreate(BaseModel):
    title: str = Field(..., max_length=200)
    type: int = Field(1, ge=1, le=4)
    content: str
    is_top: int = Field(0, ge=0, le=1)
    status: int = Field(0, ge=0, le=1)


class NoticeResponse(BaseModel):
    id: str
    title: str
    type: int
    content: Optional[str] = None
    is_top: int = 0
    status: int = 0
    publish_time: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BannerCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    image_url: str
    link_type: int = Field(0, ge=0, le=3)
    link_url: Optional[str] = None
    position: str = "home"
    sort_order: int = Field(0, ge=0)
    status: int = Field(1, ge=0, le=1)


class BannerResponse(BaseModel):
    id: str
    title: Optional[str] = None
    image_url: str
    link_type: int = 0
    link_url: Optional[str] = None
    position: str = "home"
    sort_order: int = 0
    status: int = 1
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 新闻管理 ==========
@router.get("/news", response_model=PageResponse[NewsResponse])
async def get_news_list(
    type: Optional[int] = None,
    status: Optional[int] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取新闻列表"""
    service = NewsService(db)
    items, total = await service.get_list(
        type=type,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        data=[NewsResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/news/published", response_model=List[NewsResponse])
async def get_published_news(
    type: Optional[int] = None,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """获取已发布新闻（前端展示）"""
    service = NewsService(db)
    items = await service.get_published(type=type, limit=limit)
    return [NewsResponse.model_validate(item) for item in items]


@router.get("/news/{news_id}", response_model=NewsResponse)
async def get_news_detail(
    news_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取新闻详情"""
    service = NewsService(db)
    news = await service.get_by_id(news_id)
    if not news:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="新闻不存在")
    
    # 增加浏览量
    await service.increment_view(news_id)
    
    return NewsResponse.model_validate(news)


@router.post("/news", response_model=NewsResponse)
async def create_news(
    data: NewsCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """创建新闻"""
    service = NewsService(db)
    news = await service.create(data.model_dump())
    return NewsResponse.model_validate(news)


@router.put("/news/{news_id}", response_model=NewsResponse)
async def update_news(
    news_id: str,
    data: NewsCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """更新新闻"""
    service = NewsService(db)
    news = await service.update(news_id, data.model_dump())
    if not news:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="新闻不存在")
    return NewsResponse.model_validate(news)


@router.delete("/news/{news_id}")
async def delete_news(
    news_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """删除新闻"""
    service = NewsService(db)
    success = await service.delete(news_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="新闻不存在")
    return {"message": "删除成功"}


# ========== 公告管理 ==========
@router.get("/notices", response_model=PageResponse[NoticeResponse])
async def get_notice_list(
    type: Optional[int] = None,
    status: Optional[int] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取公告列表"""
    service = NoticeService(db)
    items, total = await service.get_list(
        type=type,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        data=[NoticeResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/notices/published", response_model=List[NoticeResponse])
async def get_published_notices(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """获取已发布公告（前端展示）"""
    service = NoticeService(db)
    items = await service.get_published(limit=limit)
    return [NoticeResponse.model_validate(item) for item in items]


@router.get("/notices/{notice_id}", response_model=NoticeResponse)
async def get_notice_detail(
    notice_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取公告详情"""
    service = NoticeService(db)
    notice = await service.get_by_id(notice_id)
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在")
    return NoticeResponse.model_validate(notice)


@router.post("/notices", response_model=NoticeResponse)
async def create_notice(
    data: NoticeCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """创建公告"""
    service = NoticeService(db)
    notice = await service.create(data.model_dump())
    return NoticeResponse.model_validate(notice)


@router.put("/notices/{notice_id}", response_model=NoticeResponse)
async def update_notice(
    notice_id: str,
    data: NoticeCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """更新公告"""
    service = NoticeService(db)
    notice = await service.update(notice_id, data.model_dump())
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在")
    return NoticeResponse.model_validate(notice)


@router.delete("/notices/{notice_id}")
async def delete_notice(
    notice_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """删除公告"""
    service = NoticeService(db)
    success = await service.delete(notice_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="公告不存在")
    return {"message": "删除成功"}


# ========== 轮播图管理 ==========
@router.get("/banners", response_model=PageResponse[BannerResponse])
async def get_banner_list(
    position: Optional[str] = None,
    status: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """获取轮播图列表"""
    service = BannerService(db)
    items, total = await service.get_list(
        position=position,
        status=status,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        data=[BannerResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/banners/active", response_model=List[BannerResponse])
async def get_active_banners(
    position: str = "home",
    db: AsyncSession = Depends(get_db),
):
    """获取启用的轮播图（前端展示）"""
    service = BannerService(db)
    items = await service.get_active(position=position)
    return [BannerResponse.model_validate(item) for item in items]


@router.post("/banners", response_model=BannerResponse)
async def create_banner(
    data: BannerCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """创建轮播图"""
    service = BannerService(db)
    banner = await service.create(data.model_dump())
    return BannerResponse.model_validate(banner)


@router.put("/banners/{banner_id}", response_model=BannerResponse)
async def update_banner(
    banner_id: str,
    data: BannerCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """更新轮播图"""
    service = BannerService(db)
    banner = await service.update(banner_id, data.model_dump())
    if not banner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="轮播图不存在")
    return BannerResponse.model_validate(banner)


@router.delete("/banners/{banner_id}")
async def delete_banner(
    banner_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """删除轮播图"""
    service = BannerService(db)
    success = await service.delete(banner_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="轮播图不存在")
    return {"message": "删除成功"}
