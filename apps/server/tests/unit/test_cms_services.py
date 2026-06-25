"""CMS 模块单元测试

覆盖范围:
- CmsSiteService:    CRUD, 列表筛选(关键词/状态), 软删除/恢复/永久删除, 批量删除
- CmsCategoryService: CRUD, 树形构建, 租户隔离, 批量排序
- CmsArticleService:  CRUD, 列表筛选(站点/栏目/门店), 草稿/发布, 浏览量递增, 版本快照, 软删除
- 边界场景: 不存在的ID, 空结果, 租户隔离, 门店过滤(站点级 vs 门店级)
"""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cms import CmsArticle, CmsCategory, CmsSite
from app.modules.cms.service import CmsArticleService, CmsCategoryService, CmsSiteService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TENANT_A = "tenant_a"
TENANT_B = "tenant_b"
SITE_A = "site_a"
STORE_1 = "store_001"


def _make_site_data(**overrides) -> dict:
    defaults = dict(
        name="官网",
        code="main",
        description="主站点",
        status=1,
        is_default=0,
    )
    defaults.update(overrides)
    return defaults


def _make_category_data(**overrides) -> dict:
    defaults = dict(
        site_id=SITE_A,
        name="关于我们",
        slug="about",
        sort_order=0,
        status=1,
    )
    defaults.update(overrides)
    return defaults


def _make_article_data(**overrides) -> dict:
    defaults = dict(
        site_id=SITE_A,
        title="文章标题",
        content="<p>正文</p>",
        summary="摘要",
        status=0,
        is_top=0,
    )
    defaults.update(overrides)
    return defaults


async def _seed_site(db: AsyncSession, tenant_id: str = TENANT_A, **overrides) -> CmsSite:
    site = CmsSite(id=str(uuid4()), tenant_id=tenant_id, **_make_site_data(**overrides))
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return site


async def _seed_category(db: AsyncSession, tenant_id: str = TENANT_A, **overrides) -> CmsCategory:
    cat = CmsCategory(id=str(uuid4()), tenant_id=tenant_id, **_make_category_data(**overrides))
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


async def _seed_article(db: AsyncSession, tenant_id: str = TENANT_A, **overrides) -> CmsArticle:
    art = CmsArticle(id=str(uuid4()), tenant_id=tenant_id, **_make_article_data(**overrides))
    db.add(art)
    await db.commit()
    await db.refresh(art)
    return art


# ---------------------------------------------------------------------------
# CmsSiteService
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCmsSiteService:
    """CmsSiteService CRUD 及筛选逻辑"""

    @pytest.mark.asyncio
    async def test_create_site(self, db_session):
        svc = CmsSiteService(db_session)
        site = await svc.create(_make_site_data(), tenant_id=TENANT_A, operator_id="admin_001")
        assert site.id is not None
        assert site.name == "官网"
        assert site.tenant_id == TENANT_A
        assert site.created_by == "admin_001"

    @pytest.mark.asyncio
    async def test_get_by_id(self, db_session):
        svc = CmsSiteService(db_session)
        created = await svc.create(_make_site_data(), tenant_id=TENANT_A)
        found = await svc.get_by_id(created.id)
        assert found is not None
        assert found.id == created.id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, db_session):
        svc = CmsSiteService(db_session)
        assert await svc.get_by_id("not-exist") is None

    @pytest.mark.asyncio
    async def test_list_keyword_and_tenant_isolation(self, db_session):
        svc = CmsSiteService(db_session)
        await svc.create(_make_site_data(name="官网", code="main"), tenant_id=TENANT_A)
        await svc.create(_make_site_data(name="活动站", code="event"), tenant_id=TENANT_A)
        await svc.create(_make_site_data(name="官网", code="main2"), tenant_id=TENANT_B)

        # 租户A全部
        items, total = await svc.get_list(tenant_id=TENANT_A)
        assert total == 2
        # 关键词
        items, total = await svc.get_list(tenant_id=TENANT_A, keyword="活动")
        assert total == 1
        assert items[0].code == "event"
        # 租户隔离
        items, total = await svc.get_list(tenant_id=TENANT_B)
        assert total == 1

    @pytest.mark.asyncio
    async def test_update_site(self, db_session):
        svc = CmsSiteService(db_session)
        created = await svc.create(_make_site_data(), tenant_id=TENANT_A)
        updated = await svc.update(created.id, {"name": "新名称", "theme_config": {"primary": "#fff"}})
        assert updated.name == "新名称"
        assert '"primary"' in updated.theme_config  # JSON 文本

    @pytest.mark.asyncio
    async def test_soft_delete_restore_permanent(self, db_session):
        svc = CmsSiteService(db_session)
        created = await svc.create(_make_site_data(), tenant_id=TENANT_A)

        assert await svc.delete(created.id) is True
        assert (await svc.get_by_id(created.id)).is_deleted is True

        assert await svc.restore(created.id) is True
        assert (await svc.get_by_id(created.id)).is_deleted is False

        assert await svc.permanent_delete(created.id) is True
        assert await svc.get_by_id(created.id) is None

    @pytest.mark.asyncio
    async def test_delete_not_found_or_already_deleted(self, db_session):
        svc = CmsSiteService(db_session)
        assert await svc.delete("nope") is False
        created = await svc.create(_make_site_data(), tenant_id=TENANT_A)
        await svc.delete(created.id)
        assert await svc.delete(created.id) is False  # 已删除


# ---------------------------------------------------------------------------
# CmsCategoryService
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCmsCategoryService:
    """CmsCategoryService CRUD 及树形构建"""

    @pytest.mark.asyncio
    async def test_create_category(self, db_session):
        svc = CmsCategoryService(db_session)
        cat = await svc.create(_make_category_data(), tenant_id=TENANT_A, operator_id="admin_001")
        assert cat.id is not None
        assert cat.tenant_id == TENANT_A
        assert cat.created_by == "admin_001"

    @pytest.mark.asyncio
    async def test_list_and_tenant_isolation(self, db_session):
        svc = CmsCategoryService(db_session)
        await svc.create(_make_category_data(name="关于", slug="about"), tenant_id=TENANT_A)
        await svc.create(_make_category_data(name="产品", slug="product"), tenant_id=TENANT_A)
        # 不同站点（site_id+slug 唯一），不同租户
        await svc.create(_make_category_data(name="关于", slug="about", site_id="site_b"), tenant_id=TENANT_B)

        items = await svc.get_list(tenant_id=TENANT_A)
        assert len(items) == 2
        items_b = await svc.get_list(tenant_id=TENANT_B)
        assert len(items_b) == 1

    @pytest.mark.asyncio
    async def test_build_tree(self, db_session):
        svc = CmsCategoryService(db_session)
        root = await svc.create(_make_category_data(name="关于我们", slug="about"), tenant_id=TENANT_A)
        child = await svc.create(
            _make_category_data(name="团队", slug="team", parent_id=root.id),
            tenant_id=TENANT_A,
        )
        await svc.create(
            _make_category_data(name="历史", slug="history", parent_id=root.id),
            tenant_id=TENANT_A,
        )

        tree = await svc.build_tree(tenant_id=TENANT_A)
        assert len(tree) == 1
        assert tree[0]["item"].id == root.id
        assert len(tree[0]["children"]) == 2

    @pytest.mark.asyncio
    async def test_update_and_delete(self, db_session):
        svc = CmsCategoryService(db_session)
        created = await svc.create(_make_category_data(), tenant_id=TENANT_A)
        updated = await svc.update(created.id, {"name": "新栏目", "sort_order": 5})
        assert updated.name == "新栏目"
        assert updated.sort_order == 5

        assert await svc.delete(created.id) is True
        assert (await svc.get_by_id(created.id)).is_deleted is True

    @pytest.mark.asyncio
    async def test_batch_sort(self, db_session):
        svc = CmsCategoryService(db_session)
        c1 = await svc.create(_make_category_data(name="A", slug="a"), tenant_id=TENANT_A)
        c2 = await svc.create(_make_category_data(name="B", slug="b"), tenant_id=TENANT_A)

        updated = await svc.batch_sort([{"id": c1.id, "sort_order": 2}, {"id": c2.id, "sort_order": 1}])
        assert updated == 2
        assert (await svc.get_by_id(c1.id)).sort_order == 2
        assert (await svc.get_by_id(c2.id)).sort_order == 1


# ---------------------------------------------------------------------------
# CmsArticleService
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCmsArticleService:
    """CmsArticleService CRUD、筛选、发布、版本、软删除"""

    @pytest.mark.asyncio
    async def test_create_article(self, db_session):
        svc = CmsArticleService(db_session)
        art = await svc.create(_make_article_data(), tenant_id=TENANT_A, operator_id="admin_001")
        assert art.id is not None
        assert art.tenant_id == TENANT_A
        assert art.status == 0  # 草稿
        assert art.publish_time is None
        assert art.created_by == "admin_001"

    @pytest.mark.asyncio
    async def test_create_published_sets_publish_time(self, db_session):
        svc = CmsArticleService(db_session)
        art = await svc.create(_make_article_data(status=1), tenant_id=TENANT_A)
        assert art.status == 1
        assert art.publish_time is not None

    @pytest.mark.asyncio
    async def test_tags_serialized_as_json(self, db_session):
        svc = CmsArticleService(db_session)
        art = await svc.create(_make_article_data(tags=["新闻", "公告"]), tenant_id=TENANT_A)
        assert '"新闻"' in art.tags  # 存储为 JSON 文本

    @pytest.mark.asyncio
    async def test_list_filters(self, db_session):
        svc = CmsArticleService(db_session)
        await svc.create(_make_article_data(title="招聘", status=1), tenant_id=TENANT_A)
        await svc.create(_make_article_data(title="活动", status=0), tenant_id=TENANT_A)
        await svc.create(_make_article_data(title="其它", status=1), tenant_id=TENANT_B)

        # 租户全部
        _, total = await svc.get_list(tenant_id=TENANT_A)
        assert total == 2
        # 状态筛选
        _, total = await svc.get_list(tenant_id=TENANT_A, status=1)
        assert total == 1
        # 关键词
        _, total = await svc.get_list(tenant_id=TENANT_A, keyword="招聘")
        assert total == 1
        # 租户隔离
        _, total = await svc.get_list(tenant_id=TENANT_B)
        assert total == 1

    @pytest.mark.asyncio
    async def test_list_store_filter(self, db_session):
        """门店过滤：命中门店 或 站点级(store_id 为空)"""
        svc = CmsArticleService(db_session)
        await svc.create(_make_article_data(store_id=None), tenant_id=TENANT_A)  # 站点级
        await svc.create(_make_article_data(store_id=STORE_1), tenant_id=TENANT_A)  # 门店级
        await svc.create(_make_article_data(store_id="store_999"), tenant_id=TENANT_A)  # 其它门店

        _, total = await svc.get_list(tenant_id=TENANT_A, store_id=STORE_1)
        assert total == 2  # 站点级 + 本门店

    @pytest.mark.asyncio
    async def test_update_writes_version_snapshot(self, db_session):
        svc = CmsArticleService(db_session)
        created = await svc.create(_make_article_data(), tenant_id=TENANT_A)
        updated = await svc.update(created.id, {"title": "新标题", "status": 1})

        assert updated.title == "新标题"
        assert updated.publish_time is not None  # 发布自动补时间

        # 版本快照应写入 content_versions
        from sqlalchemy import select
        from app.models.content_version import ContentVersion

        result = await db_session.execute(
            select(ContentVersion).where(
                ContentVersion.content_type == "cms_article",
                ContentVersion.content_id == created.id,
            )
        )
        versions = result.scalars().all()
        assert len(versions) == 1

    @pytest.mark.asyncio
    async def test_increment_view(self, db_session):
        svc = CmsArticleService(db_session)
        created = await svc.create(_make_article_data(), tenant_id=TENANT_A)
        assert created.view_count == 0
        await svc.increment_view(created.id)
        await svc.increment_view(created.id)
        assert (await svc.get_by_id(created.id)).view_count == 2

    @pytest.mark.asyncio
    async def test_trash_only_returns_deleted(self, db_session):
        """回收站语义：deleted_only=True 只返回已删除文章"""
        svc = CmsArticleService(db_session)
        a1 = await svc.create(_make_article_data(title="保留"), tenant_id=TENANT_A)
        a2 = await svc.create(_make_article_data(title="已删"), tenant_id=TENANT_A)
        await svc.delete(a2.id)

        # 正常列表：只 a1
        _, total = await svc.get_list(tenant_id=TENANT_A)
        assert total == 1
        # 回收站：只 a2
        items, total = await svc.get_list(tenant_id=TENANT_A, deleted_only=True)
        assert total == 1
        assert items[0].id == a2.id
        # include_deleted：全部 2 条
        _, total = await svc.get_list(tenant_id=TENANT_A, include_deleted=True)
        assert total == 2

    @pytest.mark.asyncio
    async def test_list_store_filter_list(self, db_session):
        """门店过滤支持多门店列表（聚合模式）"""
        svc = CmsArticleService(db_session)
        await svc.create(_make_article_data(store_id=None), tenant_id=TENANT_A)
        await svc.create(_make_article_data(store_id="store_1"), tenant_id=TENANT_A)
        await svc.create(_make_article_data(store_id="store_2"), tenant_id=TENANT_A)
        await svc.create(_make_article_data(store_id="store_999"), tenant_id=TENANT_A)

        # 聚合 store_1 + store_2：命中 2 条门店级 + 1 条站点级 = 3
        _, total = await svc.get_list(tenant_id=TENANT_A, store_id=["store_1", "store_2"])
        assert total == 3

    @pytest.mark.asyncio
    async def test_soft_delete_and_batch_delete(self, db_session):
        svc = CmsArticleService(db_session)
        a1 = await svc.create(_make_article_data(), tenant_id=TENANT_A)
        a2 = await svc.create(_make_article_data(), tenant_id=TENANT_A)

        assert await svc.delete(a1.id) is True
        assert (await svc.get_by_id(a1.id)).is_deleted is True

        count = await svc.batch_delete([a2.id, "not-exist"])
        assert count == 1
        assert (await svc.get_by_id(a2.id)).is_deleted is True

    @pytest.mark.asyncio
    async def test_restore_and_permanent_delete(self, db_session):
        svc = CmsArticleService(db_session)
        created = await svc.create(_make_article_data(), tenant_id=TENANT_A)
        await svc.delete(created.id)

        assert await svc.restore(created.id) is True
        assert (await svc.get_by_id(created.id)).is_deleted is False

        assert await svc.permanent_delete(created.id) is True
        assert await svc.get_by_id(created.id) is None

    @pytest.mark.asyncio
    async def test_get_published(self, db_session):
        svc = CmsArticleService(db_session)
        await svc.create(_make_article_data(title="已发布", status=1), tenant_id=TENANT_A)
        await svc.create(_make_article_data(title="草稿", status=0), tenant_id=TENANT_A)

        published = await svc.get_published(site_id=SITE_A, limit=10)
        assert len(published) == 1
        assert published[0].title == "已发布"
