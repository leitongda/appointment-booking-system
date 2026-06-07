"""Content 模块单元测试

覆盖范围:
- NewsService: CRUD, 列表筛选, 发布/取消发布, 浏览量递增, 置顶排序
- NoticeService: CRUD, 列表筛选, 发布控制
- BannerService: CRUD, 位置筛选, 排序, 启用状态
- 边界场景: 不存在的ID, 空结果, store_id 隔离(全局 vs 门店), 分页, 关键词搜索
"""

from datetime import datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Banner, News, Notice
from app.modules.content.service import BannerService, NewsService, NoticeService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_news_data(**overrides) -> dict:
    """生成新闻创建所需字典"""
    defaults = dict(
        title="测试新闻标题",
        content="<p>新闻正文内容</p>",
        type=1,
        summary="新闻摘要",
        cover_image="https://example.com/cover.jpg",
        is_top=0,
        status=0,
    )
    defaults.update(overrides)
    return defaults


def _make_notice_data(**overrides) -> dict:
    """生成公告创建所需字典"""
    defaults = dict(
        title="测试公告标题",
        content="<p>公告正文内容</p>",
        type=1,
        is_top=0,
        status=0,
    )
    defaults.update(overrides)
    return defaults


def _make_banner_data(**overrides) -> dict:
    """生成轮播图创建所需字典"""
    defaults = dict(
        image_url="https://example.com/banner.jpg",
        title="测试轮播图",
        link_type=0,
        link_url=None,
        position="home",
        sort_order=0,
        status=1,
    )
    defaults.update(overrides)
    return defaults


async def _seed_news(db: AsyncSession, count: int = 3, **overrides) -> list:
    """批量创建新闻并返回"""
    items = []
    for i in range(count):
        data = _make_news_data(
            title=f"新闻{i+1}",
            status=overrides.get("status", 0),
            type=overrides.get("type", 1),
            is_top=overrides.get("is_top", 0),
        )
        data.update({k: v for k, v in overrides.items() if k not in ("status", "type", "is_top")})
        news = News(
            id=str(uuid4()),
            title=data["title"],
            content=data["content"],
            type=data["type"],
            summary=data.get("summary"),
            cover_image=data.get("cover_image"),
            is_top=data["is_top"],
            status=data["status"],
            store_id=overrides.get("store_id"),
        )
        db.add(news)
        items.append(news)
    await db.commit()
    for item in items:
        await db.refresh(item)
    return items


# ---------------------------------------------------------------------------
# TestNewsService
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestNewsService:
    """NewsService CRUD 及筛选逻辑"""

    @pytest.mark.asyncio
    async def test_create_news(self, db_session):
        """创建新闻 -- Happy path"""
        svc = NewsService(db_session)
        data = _make_news_data()
        news = await svc.create(data, store_id="store_001", operator_id="admin_001")

        assert news.id is not None
        assert news.title == "测试新闻标题"
        assert news.content == "<p>新闻正文内容</p>"
        assert news.type == 1
        assert news.status == 0  # 草稿
        assert news.publish_time is None
        assert news.store_id == "store_001"
        assert news.created_by == "admin_001"

    @pytest.mark.asyncio
    async def test_create_news_auto_publish_time(self, db_session):
        """创建新闻时直接发布，publish_time 应自动设置"""
        svc = NewsService(db_session)
        data = _make_news_data(status=1)
        news = await svc.create(data)

        assert news.status == 1
        assert news.publish_time is not None

    @pytest.mark.asyncio
    async def test_get_by_id(self, db_session):
        """根据 ID 获取新闻"""
        svc = NewsService(db_session)
        created = await svc.create(_make_news_data(title="详情测试"))
        found = await svc.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id
        assert found.title == "详情测试"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, db_session):
        """查询不存在的 ID 返回 None"""
        svc = NewsService(db_session)
        found = await svc.get_by_id(str(uuid4()))
        assert found is None

    @pytest.mark.asyncio
    async def test_update_news(self, db_session):
        """更新新闻字段"""
        svc = NewsService(db_session)
        created = await svc.create(_make_news_data())

        updated = await svc.update(
            created.id,
            {"title": "更新后标题", "summary": "更新后摘要"},
            operator_id="admin_002",
        )

        assert updated is not None
        assert updated.title == "更新后标题"
        assert updated.summary == "更新后摘要"
        assert updated.updated_by == "admin_002"

    @pytest.mark.asyncio
    async def test_update_news_not_found(self, db_session):
        """更新不存在的新闻返回 None"""
        svc = NewsService(db_session)
        result = await svc.update(str(uuid4()), {"title": "x"})
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_news(self, db_session):
        """软删除新闻（移入回收站）"""
        svc = NewsService(db_session)
        created = await svc.create(_make_news_data())
        success = await svc.delete(created.id)

        assert success is True
        # 软删除后 get_by_id 仍返回对象，但 is_deleted=True
        deleted = await svc.get_by_id(created.id)
        assert deleted is not None
        assert deleted.is_deleted is True
        assert deleted.deleted_at is not None
        # 普通列表查询不可见
        items, total = await svc.get_list()
        assert total == 0

    @pytest.mark.asyncio
    async def test_delete_news_not_found(self, db_session):
        """删除不存在的新闻返回 False"""
        svc = NewsService(db_session)
        assert await svc.delete(str(uuid4())) is False

    @pytest.mark.asyncio
    async def test_publish_and_unpublish(self, db_session):
        """发布/取消发布状态切换"""
        svc = NewsService(db_session)
        created = await svc.create(_make_news_data(status=0))
        assert created.status == 0
        assert created.publish_time is None

        # 发布
        published = await svc.update(created.id, {"status": 1})
        assert published.status == 1
        assert published.publish_time is not None

        # 取消发布
        draft = await svc.update(created.id, {"status": 0})
        assert draft.status == 0

    @pytest.mark.asyncio
    async def test_get_list_filters(self, db_session, test_store):
        """列表筛选: type + status + keyword + store_id"""
        svc = NewsService(db_session)
        await _seed_news(db_session, count=5, status=0, type=1)
        await _seed_news(db_session, count=3, status=1, type=2, store_id=test_store.id)

        # 按 status 筛选
        items, total = await svc.get_list(status=1)
        assert total == 3
        assert all(n.status == 1 for n in items)

        # 按 type 筛选
        items, total = await svc.get_list(type=2)
        assert total == 3
        assert all(n.type == 2 for n in items)

        # 按 keyword 筛选
        items, total = await svc.get_list(keyword="新闻1")
        assert total >= 1

    @pytest.mark.asyncio
    async def test_get_list_store_filter_includes_global(self, db_session, test_store):
        """store_id 筛选应包含全局内容 (store_id IS NULL)"""
        svc = NewsService(db_session)
        # 一条全局新闻
        await svc.create(_make_news_data(title="全局新闻"))
        # 一条门店专属新闻
        await svc.create(_make_news_data(title="门店新闻"), store_id=test_store.id)

        items, total = await svc.get_list(store_id=test_store.id)
        # 全局 + 门店专属都应返回
        assert total == 2

    @pytest.mark.asyncio
    async def test_get_list_pagination(self, db_session):
        """分页: page + page_size"""
        svc = NewsService(db_session)
        await _seed_news(db_session, count=10, status=0)

        items_p1, total = await svc.get_list(page=1, page_size=3)
        items_p2, _ = await svc.get_list(page=2, page_size=3)

        assert total == 10
        assert len(items_p1) == 3
        assert len(items_p2) == 3
        assert items_p1[0].id != items_p2[0].id

    @pytest.mark.asyncio
    async def test_get_published_only_returns_status_1(self, db_session):
        """get_published 只返回 status=1 的新闻"""
        svc = NewsService(db_session)
        await _seed_news(db_session, count=3, status=0)
        await _seed_news(db_session, count=2, status=1)

        published = await svc.get_published()
        assert len(published) == 2
        assert all(n.status == 1 for n in published)

    @pytest.mark.asyncio
    async def test_increment_view(self, db_session):
        """浏览量递增"""
        svc = NewsService(db_session)
        created = await svc.create(_make_news_data())
        assert created.view_count == 0

        await svc.increment_view(created.id)
        await svc.increment_view(created.id)

        refreshed = await svc.get_by_id(created.id)
        assert refreshed.view_count == 2

    @pytest.mark.asyncio
    async def test_increment_view_not_found(self, db_session):
        """浏览不存在的新闻 -- 静默不报错"""
        svc = NewsService(db_session)
        # 不应抛异常
        await svc.increment_view(str(uuid4()))

    @pytest.mark.asyncio
    async def test_get_list_order_by_is_top(self, db_session):
        """列表默认按 is_top DESC, created_at DESC 排序"""
        svc = NewsService(db_session)
        normal = await svc.create(_make_news_data(title="普通新闻", is_top=0))
        topped = await svc.create(_make_news_data(title="置顶新闻", is_top=1))

        items, _ = await svc.get_list()
        assert items[0].id == topped.id
        assert items[1].id == normal.id


# ---------------------------------------------------------------------------
# TestNoticeService
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestNoticeService:
    """NoticeService CRUD 及筛选逻辑"""

    @pytest.mark.asyncio
    async def test_create_notice(self, db_session):
        """创建公告"""
        svc = NoticeService(db_session)
        data = _make_notice_data()
        notice = await svc.create(data, store_id="store_002", operator_id="admin_003")

        assert notice.id is not None
        assert notice.title == "测试公告标题"
        assert notice.store_id == "store_002"
        assert notice.status == 0

    @pytest.mark.asyncio
    async def test_create_notice_auto_publish_time(self, db_session):
        """直接发布的公告自动设置 publish_time"""
        svc = NoticeService(db_session)
        notice = await svc.create(_make_notice_data(status=1))
        assert notice.publish_time is not None

    @pytest.mark.asyncio
    async def test_update_notice(self, db_session):
        """更新公告"""
        svc = NoticeService(db_session)
        created = await svc.create(_make_notice_data())
        updated = await svc.update(created.id, {"title": "更新公告"})

        assert updated.title == "更新公告"

    @pytest.mark.asyncio
    async def test_delete_notice(self, db_session):
        """软删除公告（移入回收站）"""
        svc = NoticeService(db_session)
        created = await svc.create(_make_notice_data())
        assert await svc.delete(created.id) is True
        # 软删除后 get_by_id 仍返回对象，但 is_deleted=True
        deleted = await svc.get_by_id(created.id)
        assert deleted is not None
        assert deleted.is_deleted is True
        assert deleted.deleted_at is not None
        # 普通列表查询不可见
        items, total = await svc.get_list()
        assert total == 0

    @pytest.mark.asyncio
    async def test_delete_notice_not_found(self, db_session):
        """删除不存在的公告返回 False"""
        svc = NoticeService(db_session)
        assert await svc.delete(str(uuid4())) is False

    @pytest.mark.asyncio
    async def test_get_published_store_filter(self, db_session, test_store):
        """已发布公告按 store_id 筛选 (含全局)"""
        svc = NoticeService(db_session)
        # 全局已发布
        await svc.create(_make_notice_data(title="全局公告", status=1))
        # 门店已发布
        await svc.create(
            _make_notice_data(title="门店公告", status=1),
            store_id=test_store.id,
        )
        # 未发布
        await svc.create(_make_notice_data(title="草稿公告", status=0))

        published = await svc.get_published(store_id=test_store.id)
        assert len(published) == 2

    @pytest.mark.asyncio
    async def test_get_list_keyword_search(self, db_session):
        """公告列表关键词搜索"""
        svc = NoticeService(db_session)
        await svc.create(_make_notice_data(title="停诊通知"))
        await svc.create(_make_notice_data(title="活动预告"))

        items, total = await svc.get_list(keyword="停诊")
        assert total == 1
        assert items[0].title == "停诊通知"


# ---------------------------------------------------------------------------
# TestBannerService
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestBannerService:
    """BannerService CRUD 及位置/状态筛选"""

    @pytest.mark.asyncio
    async def test_create_banner(self, db_session):
        """创建轮播图"""
        svc = BannerService(db_session)
        data = _make_banner_data()
        banner = await svc.create(data, store_id="store_003")

        assert banner.id is not None
        assert banner.image_url == "https://example.com/banner.jpg"
        assert banner.position == "home"
        assert banner.store_id == "store_003"
        assert banner.status == 1

    @pytest.mark.asyncio
    async def test_update_banner(self, db_session):
        """更新轮播图"""
        svc = BannerService(db_session)
        created = await svc.create(_make_banner_data())
        updated = await svc.update(created.id, {"title": "新轮播图", "sort_order": 5})

        assert updated.title == "新轮播图"
        assert updated.sort_order == 5

    @pytest.mark.asyncio
    async def test_delete_banner(self, db_session):
        """软删除轮播图（移入回收站）"""
        svc = BannerService(db_session)
        created = await svc.create(_make_banner_data())
        assert await svc.delete(created.id) is True
        # 软删除后 get_by_id 仍返回对象，但 is_deleted=True
        deleted = await svc.get_by_id(created.id)
        assert deleted is not None
        assert deleted.is_deleted is True
        assert deleted.deleted_at is not None
        # 普通列表查询不可见
        items, total = await svc.get_list()
        assert total == 0

    @pytest.mark.asyncio
    async def test_delete_banner_not_found(self, db_session):
        """删除不存在的轮播图返回 False"""
        svc = BannerService(db_session)
        assert await svc.delete(str(uuid4())) is False

    @pytest.mark.asyncio
    async def test_get_active_by_position(self, db_session):
        """get_active 按 position + status=1 筛选"""
        svc = BannerService(db_session)
        await svc.create(_make_banner_data(position="home", status=1))
        await svc.create(_make_banner_data(position="home", status=0))
        await svc.create(_make_banner_data(position="department", status=1))

        active = await svc.get_active(position="home")
        assert len(active) == 1
        assert active[0].position == "home"
        assert active[0].status == 1

    @pytest.mark.asyncio
    async def test_get_active_store_filter_includes_global(self, db_session, test_store):
        """get_active 包含全局(store_id=None)和门店专属"""
        svc = BannerService(db_session)
        await svc.create(_make_banner_data(position="home", status=1))
        await svc.create(
            _make_banner_data(position="home", status=1),
            store_id=test_store.id,
        )

        active = await svc.get_active(position="home", store_id=test_store.id)
        assert len(active) == 2

    @pytest.mark.asyncio
    async def test_get_list_order_by_sort_order(self, db_session):
        """列表按 sort_order ASC 排序"""
        svc = BannerService(db_session)
        b2 = await svc.create(_make_banner_data(sort_order=20))
        b1 = await svc.create(_make_banner_data(sort_order=5))
        b3 = await svc.create(_make_banner_data(sort_order=50))

        items, total = await svc.get_list()
        assert total == 3
        assert [b.id for b in items] == [b1.id, b2.id, b3.id]

    @pytest.mark.asyncio
    async def test_get_list_position_filter(self, db_session):
        """列表按 position 筛选"""
        svc = BannerService(db_session)
        await svc.create(_make_banner_data(position="home"))
        await svc.create(_make_banner_data(position="home"))
        await svc.create(_make_banner_data(position="profile"))

        items, total = await svc.get_list(position="home")
        assert total == 2
        assert all(b.position == "home" for b in items)

    @pytest.mark.asyncio
    async def test_get_list_empty_result(self, db_session):
        """无匹配数据时返回空列表"""
        svc = BannerService(db_session)
        items, total = await svc.get_list(status=99)
        assert items == []
        assert total == 0
