"""内容管理服务"""
import json
import uuid
from datetime import datetime

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Banner, News, Notice
from app.models.content_version import ContentVersion
from app.utils.audit import set_create_audit, set_update_audit


def _make_snapshot(model_instance) -> dict:
    """将模型实例转为可序列化的快照字典（排除 is_deleted / deleted_at）"""
    snapshot = {}
    for col in model_instance.__table__.columns:
        if col.name in ("is_deleted", "deleted_at"):
            continue
        val = getattr(model_instance, col.name)
        if isinstance(val, datetime):
            val = val.isoformat()
        snapshot[col.name] = val
    return snapshot


# ========== 新闻服务 ==========
class NewsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        type: int | None = None,
        status: int | None = None,
        keyword: str | None = None,
        store_id: str | None = None,
        page: int = 1,
        page_size: int = 10,
        include_deleted: bool = False,
    ) -> tuple[list[News], int]:
        """获取新闻列表"""
        query = select(News)
        conditions = []

        if not include_deleted:
            conditions.append(News.is_deleted == False)  # noqa: E712

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
            conditions.append(
                or_(News.store_id == store_id, News.store_id.is_(None))
            )

        if conditions:
            query = query.where(and_(*conditions))

        count_query = select(func.count(News.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await self.db.scalar(count_query)

        query = query.order_by(News.is_top.desc(), News.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total or 0

    async def get_trash_list(
        self,
        store_id: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[News], int]:
        """获取回收站新闻列表"""
        return await self.get_list(
            store_id=store_id, page=page, page_size=page_size, include_deleted=True
        )

    async def get_published(
        self,
        type: int | None = None,
        store_id: str | None = None,
        limit: int = 10,
    ) -> list[News]:
        """获取已发布的新闻"""
        conditions = [News.status == 1, News.is_deleted == False]  # noqa: E712

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

    async def get_by_id(self, news_id: str) -> News | None:
        """获取新闻详情"""
        return await self.db.get(News, news_id)

    async def create(self, data: dict, store_id: str | None = None, operator_id: str | None = None) -> News:
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

    async def update(self, news_id: str, data: dict, operator_id: str | None = None) -> News | None:
        """更新新闻（更新前保存版本快照）"""
        news = await self.get_by_id(news_id)
        if not news:
            return None

        # 保存版本快照
        snapshot = _make_snapshot(news)
        version = ContentVersion(
            id=str(uuid.uuid4()),
            content_type="news",
            content_id=news_id,
            operator_id=operator_id,
            snapshot=json.dumps(snapshot, ensure_ascii=False),
        )
        self.db.add(version)

        for key, value in data.items():
            if hasattr(news, key) and value is not None:
                setattr(news, key, value)

        if data.get("status") == 1 and not news.publish_time:
            news.publish_time = datetime.now()

        set_update_audit(news, operator_id)
        await self.db.commit()
        await self.db.refresh(news)
        return news

    async def delete(self, news_id: str) -> bool:
        """软删除新闻（移入回收站）"""
        news = await self.get_by_id(news_id)
        if not news or news.is_deleted:
            return False

        news.is_deleted = True
        news.deleted_at = datetime.now()
        set_update_audit(news)
        await self.db.commit()
        return True

    async def restore(self, news_id: str) -> bool:
        """从回收站恢复新闻"""
        news = await self.get_by_id(news_id)
        if not news or not news.is_deleted:
            return False

        news.is_deleted = False
        news.deleted_at = None
        set_update_audit(news)
        await self.db.commit()
        return True

    async def permanent_delete(self, news_id: str) -> bool:
        """永久删除新闻"""
        news = await self.get_by_id(news_id)
        if not news:
            return False

        await self.db.delete(news)
        await self.db.commit()
        return True

    async def increment_view(self, news_id: str) -> None:
        """增加浏览量（原子递增，避免并发竞态）"""
        await self.db.execute(
            update(News).where(News.id == news_id).values(view_count=News.view_count + 1)
        )
        await self.db.commit()

    async def batch_delete(self, ids: list[str]) -> int:
        """批量软删除新闻，返回实际删除数量"""
        deleted_count = 0
        for news_id in ids:
            news = await self.get_by_id(news_id)
            if news and not news.is_deleted:
                news.is_deleted = True
                news.deleted_at = datetime.now()
                set_update_audit(news)
                deleted_count += 1
        if deleted_count > 0:
            await self.db.commit()
        return deleted_count


# ========== 公告服务 ==========
class NoticeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        type: int | None = None,
        status: int | None = None,
        keyword: str | None = None,
        store_id: str | None = None,
        page: int = 1,
        page_size: int = 10,
        include_deleted: bool = False,
    ) -> tuple[list[Notice], int]:
        """获取公告列表"""
        query = select(Notice)
        conditions = []

        if not include_deleted:
            conditions.append(Notice.is_deleted == False)  # noqa: E712

        if type is not None:
            conditions.append(Notice.type == type)
        if status is not None:
            conditions.append(Notice.status == status)
        if keyword:
            # #10 搜索增强：keyword 同时匹配 title 和 content
            conditions.append(
                or_(
                    Notice.title.ilike(f"%{keyword}%"),
                    Notice.content.ilike(f"%{keyword}%"),
                )
            )
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

    async def get_trash_list(
        self,
        store_id: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[Notice], int]:
        """获取回收站公告列表"""
        return await self.get_list(
            store_id=store_id, page=page, page_size=page_size, include_deleted=True
        )

    async def get_published(self, store_id: str | None = None, limit: int = 10) -> list[Notice]:
        """获取已发布的公告"""
        conditions = [Notice.status == 1, Notice.is_deleted == False]  # noqa: E712

        if store_id:
            conditions.append(
                or_(Notice.store_id == store_id, Notice.store_id.is_(None))
            )

        query = select(Notice).where(and_(*conditions))
        query = query.order_by(Notice.is_top.desc(), Notice.publish_time.desc())
        query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, notice_id: str) -> Notice | None:
        """获取公告详情"""
        return await self.db.get(Notice, notice_id)

    async def create(self, data: dict, store_id: str | None = None, operator_id: str | None = None) -> Notice:
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

    async def update(self, notice_id: str, data: dict, operator_id: str | None = None) -> Notice | None:
        """更新公告（更新前保存版本快照）"""
        notice = await self.get_by_id(notice_id)
        if not notice:
            return None

        # 保存版本快照
        snapshot = _make_snapshot(notice)
        version = ContentVersion(
            id=str(uuid.uuid4()),
            content_type="notice",
            content_id=notice_id,
            operator_id=operator_id,
            snapshot=json.dumps(snapshot, ensure_ascii=False),
        )
        self.db.add(version)

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
        """软删除公告（移入回收站）"""
        notice = await self.get_by_id(notice_id)
        if not notice or notice.is_deleted:
            return False

        notice.is_deleted = True
        notice.deleted_at = datetime.now()
        set_update_audit(notice)
        await self.db.commit()
        return True

    async def restore(self, notice_id: str) -> bool:
        """从回收站恢复公告"""
        notice = await self.get_by_id(notice_id)
        if not notice or not notice.is_deleted:
            return False

        notice.is_deleted = False
        notice.deleted_at = None
        set_update_audit(notice)
        await self.db.commit()
        return True

    async def permanent_delete(self, notice_id: str) -> bool:
        """永久删除公告"""
        notice = await self.get_by_id(notice_id)
        if not notice:
            return False

        await self.db.delete(notice)
        await self.db.commit()
        return True

    async def increment_view(self, notice_id: str) -> None:
        """增加浏览量（原子递增，避免并发竞态）"""
        await self.db.execute(
            update(Notice).where(Notice.id == notice_id).values(view_count=Notice.view_count + 1)
        )
        await self.db.commit()

    async def batch_delete(self, ids: list[str]) -> int:
        """批量软删除公告，返回实际删除数量"""
        deleted_count = 0
        for notice_id in ids:
            notice = await self.get_by_id(notice_id)
            if notice and not notice.is_deleted:
                notice.is_deleted = True
                notice.deleted_at = datetime.now()
                set_update_audit(notice)
                deleted_count += 1
        if deleted_count > 0:
            await self.db.commit()
        return deleted_count


# ========== 轮播图服务 ==========
class BannerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        position: str | None = None,
        status: int | None = None,
        store_id: str | None = None,
        page: int = 1,
        page_size: int = 10,
        include_deleted: bool = False,
    ) -> tuple[list[Banner], int]:
        """获取轮播图列表"""
        query = select(Banner)
        conditions = []

        if not include_deleted:
            conditions.append(Banner.is_deleted == False)  # noqa: E712

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

    async def get_trash_list(
        self,
        store_id: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[Banner], int]:
        """获取回收站轮播图列表"""
        return await self.get_list(
            store_id=store_id, page=page, page_size=page_size, include_deleted=True
        )

    async def get_active(self, position: str = "home", store_id: str | None = None) -> list[Banner]:
        """获取启用的轮播图"""
        conditions = [
            Banner.position == position,
            Banner.status == 1,
            Banner.is_deleted == False,  # noqa: E712
        ]

        if store_id:
            conditions.append(
                or_(Banner.store_id == store_id, Banner.store_id.is_(None))
            )

        query = select(Banner).where(and_(*conditions))
        query = query.order_by(Banner.sort_order.asc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, banner_id: str) -> Banner | None:
        """获取轮播图详情"""
        return await self.db.get(Banner, banner_id)

    async def create(self, data: dict, store_id: str | None = None, operator_id: str | None = None) -> Banner:
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

    async def update(self, banner_id: str, data: dict, operator_id: str | None = None) -> Banner | None:
        """更新轮播图（更新前保存版本快照）"""
        banner = await self.get_by_id(banner_id)
        if not banner:
            return None

        # 保存版本快照
        snapshot = _make_snapshot(banner)
        version = ContentVersion(
            id=str(uuid.uuid4()),
            content_type="banner",
            content_id=banner_id,
            operator_id=operator_id,
            snapshot=json.dumps(snapshot, ensure_ascii=False),
        )
        self.db.add(version)

        for key, value in data.items():
            if hasattr(banner, key) and value is not None:
                setattr(banner, key, value)

        set_update_audit(banner, operator_id)
        await self.db.commit()
        await self.db.refresh(banner)
        return banner

    async def delete(self, banner_id: str) -> bool:
        """软删除轮播图（移入回收站）"""
        banner = await self.get_by_id(banner_id)
        if not banner or banner.is_deleted:
            return False

        banner.is_deleted = True
        banner.deleted_at = datetime.now()
        set_update_audit(banner)
        await self.db.commit()
        return True

    async def restore(self, banner_id: str) -> bool:
        """从回收站恢复轮播图"""
        banner = await self.get_by_id(banner_id)
        if not banner or not banner.is_deleted:
            return False

        banner.is_deleted = False
        banner.deleted_at = None
        set_update_audit(banner)
        await self.db.commit()
        return True

    async def permanent_delete(self, banner_id: str) -> bool:
        """永久删除轮播图"""
        banner = await self.get_by_id(banner_id)
        if not banner:
            return False

        await self.db.delete(banner)
        await self.db.commit()
        return True

    async def batch_delete(self, ids: list[str]) -> int:
        """批量软删除轮播图，返回实际删除数量"""
        deleted_count = 0
        for banner_id in ids:
            banner = await self.get_by_id(banner_id)
            if banner and not banner.is_deleted:
                banner.is_deleted = True
                banner.deleted_at = datetime.now()
                set_update_audit(banner)
                deleted_count += 1
        if deleted_count > 0:
            await self.db.commit()
        return deleted_count

    async def update_sort_order(self, items: list[dict]) -> int:
        """批量更新轮播图排序，items 为 [{id, sort_order}] 列表，返回更新数量"""
        updated_count = 0
        for item in items:
            banner = await self.get_by_id(item["id"])
            if banner:
                banner.sort_order = item["sort_order"]
                set_update_audit(banner)
                updated_count += 1
        if updated_count > 0:
            await self.db.commit()
        return updated_count
