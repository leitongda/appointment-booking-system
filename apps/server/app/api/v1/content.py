from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from app.db.session import get_db

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

class NoticeCreate(BaseModel):
    title: str = Field(..., max_length=200)
    type: int = Field(1, ge=1, le=4)
    content: str
    is_top: int = Field(0, ge=0, le=1)
    status: int = Field(0, ge=0, le=1)

class BannerCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    image_url: str
    link_type: int = Field(0, ge=0, le=3)
    link_url: Optional[str] = None
    position: str = "home"
    sort_order: int = Field(0, ge=0)
    status: int = Field(1, ge=0, le=1)

# ========== 新闻管理 ==========
@router.get("/news")
async def get_news_list(
    type: Optional[int] = None,
    status: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取新闻列表"""
    # TODO: 实现数据库查询
    return {"data": [], "total": 0, "page": page, "page_size": page_size}

@router.get("/news/published")
async def get_published_news(
    type: Optional[int] = None,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """获取已发布新闻（前端展示）"""
    return []

@router.get("/news/{news_id}")
async def get_news_detail(news_id: str, db: AsyncSession = Depends(get_db)):
    """获取新闻详情"""
    return {"id": news_id, "title": "示例新闻"}

@router.post("/news")
async def create_news(data: NewsCreate, db: AsyncSession = Depends(get_db)):
    """创建新闻"""
    return {"id": "new_id", "message": "创建成功"}

@router.put("/news/{news_id}")
async def update_news(news_id: str, data: NewsCreate, db: AsyncSession = Depends(get_db)):
    """更新新闻"""
    return {"message": "更新成功"}

@router.delete("/news/{news_id}")
async def delete_news(news_id: str, db: AsyncSession = Depends(get_db)):
    """删除新闻"""
    return {"message": "删除成功"}

# ========== 公告管理 ==========
@router.get("/notices")
async def get_notice_list(
    type: Optional[int] = None,
    status: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取公告列表"""
    return {"data": [], "total": 0, "page": page, "page_size": page_size}

@router.get("/notices/published")
async def get_published_notices(limit: int = Query(10, ge=1, le=50), db: AsyncSession = Depends(get_db)):
    """获取已发布公告（前端展示）"""
    return []

@router.get("/notices/{notice_id}")
async def get_notice_detail(notice_id: str, db: AsyncSession = Depends(get_db)):
    """获取公告详情"""
    return {"id": notice_id, "title": "示例公告"}

@router.post("/notices")
async def create_notice(data: NoticeCreate, db: AsyncSession = Depends(get_db)):
    """创建公告"""
    return {"id": "new_id", "message": "创建成功"}

@router.put("/notices/{notice_id}")
async def update_notice(notice_id: str, data: NoticeCreate, db: AsyncSession = Depends(get_db)):
    """更新公告"""
    return {"message": "更新成功"}

@router.delete("/notices/{notice_id}")
async def delete_notice(notice_id: str, db: AsyncSession = Depends(get_db)):
    """删除公告"""
    return {"message": "删除成功"}

# ========== 轮播图管理 ==========
@router.get("/banners")
async def get_banner_list(
    position: Optional[str] = None,
    status: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取轮播图列表"""
    return {"data": [], "total": 0, "page": page, "page_size": page_size}

@router.get("/banners/active")
async def get_active_banners(position: str = "home", db: AsyncSession = Depends(get_db)):
    """获取启用的轮播图（前端展示）"""
    return []

@router.post("/banners")
async def create_banner(data: BannerCreate, db: AsyncSession = Depends(get_db)):
    """创建轮播图"""
    return {"id": "new_id", "message": "创建成功"}

@router.put("/banners/{banner_id}")
async def update_banner(banner_id: str, data: BannerCreate, db: AsyncSession = Depends(get_db)):
    """更新轮播图"""
    return {"message": "更新成功"}

@router.delete("/banners/{banner_id}")
async def delete_banner(banner_id: str, db: AsyncSession = Depends(get_db)):
    """删除轮播图"""
    return {"message": "删除成功"}

