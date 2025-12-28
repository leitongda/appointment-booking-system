"""内容管理服务"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from datetime import datetime
import uuid

from app.models.content import News, Notice, Banner
from app.utils.audit import set_create_audit, set_update_audit


# ========== 新闻服务 ==========
class NewsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        type: Optional[int] = None,
        status: Optional[int] = None,
        keyword: Optional[str] = None,
        store_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[News], int]:
        """获取新闻列表"""
        query = select(News)
        conditions = []
        
        if type is not None:
            conditions.append(News.type == type)
        if status is not None:
            conditions.append(News.status == status)
        if keyword:
            conditions.append(
                or_(
                    News.title.ilike(f"%{keyword}%"),
                    News.summary.ilike(f"%{keyword}%")
                )
            )
        if store_id:
            # 查询门店专属和全局的新闻
            conditions.append(
                or_(News.store_id == store_id, News.store_id.is_(None))
            )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # 统计总数
        count_query = select(func.count(News.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await self.db.scalar(count_query)
        
        # 分页查询
        query = query.order_by(News.is_top.desc(), News.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return list(items), total or 0

    async def get_published(
        self,
        type: Optional[int] = None,
        store_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[News]:
        """获取已发布的新闻"""
        conditions = [News.status == 1]
        
        if type is not None:
            conditions.append(News.type == type)
        
        if store_id:
            conditions.append(
                or_(News.store_id == store_id, News.store_id.is_(None))
            )
        
        query = select(News).where(and_(*conditions))
        query = query.order_by(News.is_top.desc(), News.publish_time.desc())
        query = query.limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, news_id: str) -> Optional[News]:
        """获取新闻详情"""
        return await self.db.get(News, news_id)

    async def create(self, data: dict, store_id: Optional[str] = None, operator_id: Optional[str] = None) -> News:
        """创建新闻"""
        news = News(
            id=str(uuid.uuid4()),
            store_id=store_id,
            title=data["title"],
            type=data.get("type", 1),
            cover_image=data.get("cover_image"),
            summary=data.get("summary"),
            content=data["content"],
            is_top=data.get("is_top", 0),
            status=data.get("status", 0),
            publish_time=datetime.now() if data.get("status") == 1 else None,
        )
        set_create_audit(news, operator_id)
        self.db.add(news)
        await self.db.commit()
        await self.db.refresh(news)
        return news

    async def update(self, news_id: str, data: dict, operator_id: Optional[str] = None) -> Optional[News]:
        """更新新闻"""
        news = await self.get_by_id(news_id)
        if not news:
            return None
        
        for key, value in data.items():
            if hasattr(news, key) and value is not None:
                setattr(news, key, value)
        
        # 首次发布时设置发布时间
        if data.get("status") == 1 and not news.publish_time:
            news.publish_time = datetime.now()
        
        set_update_audit(news, operator_id)
        await self.db.commit()
        await self.db.refresh(news)
        return news

    async def delete(self, news_id: str) -> bool:
        """删除新闻"""
        news = await self.get_by_id(news_id)
        if not news:
            return False
        
        await self.db.delete(news)
        await self.db.commit()
        return True

    async def increment_view(self, news_id: str) -> None:
        """增加浏览量"""
        news = await self.get_by_id(news_id)
        if news:
            news.view_count = (news.view_count or 0) + 1
            await self.db.commit()


# ========== 公告服务 ==========
class NoticeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        type: Optional[int] = None,
        status: Optional[int] = None,
        keyword: Optional[str] = None,
        store_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Notice], int]:
        """获取公告列表"""
        query = select(Notice)
        conditions = []
        
        if type is not None:
            conditions.append(Notice.type == type)
        if status is not None:
            conditions.append(Notice.status == status)
        if keyword:
            conditions.append(Notice.title.ilike(f"%{keyword}%"))
        if store_id:
            conditions.append(
                or_(Notice.store_id == store_id, Notice.store_id.is_(None))
            )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        count_query = select(func.count(Notice.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await self.db.scalar(count_query)
        
        query = query.order_by(Notice.is_top.desc(), Notice.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return list(items), total or 0

    async def get_published(self, store_id: Optional[str] = None, limit: int = 10) -> List[Notice]:
        """获取已发布的公告"""
        conditions = [Notice.status == 1]
        
        if store_id:
            conditions.append(
                or_(Notice.store_id == store_id, Notice.store_id.is_(None))
            )
        
        query = select(Notice).where(and_(*conditions))
        query = query.order_by(Notice.is_top.desc(), Notice.publish_time.desc())
        query = query.limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, notice_id: str) -> Optional[Notice]:
        """获取公告详情"""
        return await self.db.get(Notice, notice_id)

    async def create(self, data: dict, store_id: Optional[str] = None, operator_id: Optional[str] = None) -> Notice:
        """创建公告"""
        notice = Notice(
            id=str(uuid.uuid4()),
            store_id=store_id,
            title=data["title"],
            type=data.get("type", 1),
            content=data["content"],
            is_top=data.get("is_top", 0),
            status=data.get("status", 0),
            publish_time=datetime.now() if data.get("status") == 1 else None,
        )
        set_create_audit(notice, operator_id)
        self.db.add(notice)
        await self.db.commit()
        await self.db.refresh(notice)
        return notice

    async def update(self, notice_id: str, data: dict, operator_id: Optional[str] = None) -> Optional[Notice]:
        """更新公告"""
        notice = await self.get_by_id(notice_id)
        if not notice:
            return None
        
        for key, value in data.items():
            if hasattr(notice, key) and value is not None:
                setattr(notice, key, value)
        
        if data.get("status") == 1 and not notice.publish_time:
            notice.publish_time = datetime.now()
        
        set_update_audit(notice, operator_id)
        await self.db.commit()
        await self.db.refresh(notice)
        return notice

    async def delete(self, notice_id: str) -> bool:
        """删除公告"""
        notice = await self.get_by_id(notice_id)
        if not notice:
            return False
        
        await self.db.delete(notice)
        await self.db.commit()
        return True


# ========== 轮播图服务 ==========
class BannerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        position: Optional[str] = None,
        status: Optional[int] = None,
        store_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Banner], int]:
        """获取轮播图列表"""
        query = select(Banner)
        conditions = []
        
        if position:
            conditions.append(Banner.position == position)
        if status is not None:
            conditions.append(Banner.status == status)
        if store_id:
            conditions.append(
                or_(Banner.store_id == store_id, Banner.store_id.is_(None))
            )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        count_query = select(func.count(Banner.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await self.db.scalar(count_query)
        
        query = query.order_by(Banner.sort_order.asc(), Banner.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return list(items), total or 0

    async def get_active(self, position: str = "home", store_id: Optional[str] = None) -> List[Banner]:
        """获取启用的轮播图"""
        conditions = [
            Banner.position == position,
            Banner.status == 1
        ]
        
        if store_id:
            conditions.append(
                or_(Banner.store_id == store_id, Banner.store_id.is_(None))
            )
        
        query = select(Banner).where(and_(*conditions))
        query = query.order_by(Banner.sort_order.asc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, banner_id: str) -> Optional[Banner]:
        """获取轮播图详情"""
        return await self.db.get(Banner, banner_id)

    async def create(self, data: dict, store_id: Optional[str] = None, operator_id: Optional[str] = None) -> Banner:
        """创建轮播图"""
        banner = Banner(
            id=str(uuid.uuid4()),
            store_id=store_id,
            title=data.get("title"),
            image_url=data["image_url"],
            link_type=data.get("link_type", 0),
            link_url=data.get("link_url"),
            position=data.get("position", "home"),
            sort_order=data.get("sort_order", 0),
            status=data.get("status", 1),
        )
        set_create_audit(banner, operator_id)
        self.db.add(banner)
        await self.db.commit()
        await self.db.refresh(banner)
        return banner

    async def update(self, banner_id: str, data: dict, operator_id: Optional[str] = None) -> Optional[Banner]:
        """更新轮播图"""
        banner = await self.get_by_id(banner_id)
        if not banner:
            return None
        
        for key, value in data.items():
            if hasattr(banner, key) and value is not None:
                setattr(banner, key, value)
        
        set_update_audit(banner, operator_id)
        await self.db.commit()
        await self.db.refresh(banner)
        return banner

    async def delete(self, banner_id: str) -> bool:
        """删除轮播图"""
        banner = await self.get_by_id(banner_id)
        if not banner:
            return False
        
        await self.db.delete(banner)
        await self.db.commit()
        return True

