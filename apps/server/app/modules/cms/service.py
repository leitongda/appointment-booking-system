"""CMS 内容站点服务（站点 / 栏目 / 文章）

参照 content 模块做软删除/版本快照，参照 contacts 模块做租户隔离。
"""
import json
import uuid
from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cms import CmsArticle, CmsCategory, CmsSite
from app.models.content_version import ContentVersion
from app.utils.audit import set_create_audit, set_update_audit


def _make_snapshot(model_instance) -> dict:
    """将模型实例转为可序列化的快照字典（排除软删除字段）"""
    snapshot = {}
    for col in model_instance.__table__.columns:
        if col.name in ("is_deleted", "deleted_at"):
            continue
        val = getattr(model_instance, col.name)
        if isinstance(val, datetime):
            val = val.isoformat()
        snapshot[col.name] = val
    return snapshot


def _dump_json(value) -> str | None:
    """将 dict/list 序列化为 JSON 字符串"""
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _store_condition(store_id: str | list[str] | None):
    """生成门店过滤条件：命中指定门店（单个或多个）或 站点级文章(store_id 为空)。

    get_store_filter 可能返回 str / list[str] / None，此处统一处理。
    """
    if isinstance(store_id, (list, tuple)):
        return or_(CmsArticle.store_id.in_(store_id), CmsArticle.store_id.is_(None))
    return or_(CmsArticle.store_id == store_id, CmsArticle.store_id.is_(None))


# ============================================================
# 站点服务
# ============================================================

class CmsSiteService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        tenant_id: str,
        keyword: str | None = None,
        status: int | None = None,
        page: int = 1,
        page_size: int = 10,
        include_deleted: bool = False,
    ) -> tuple[list[CmsSite], int]:
        """获取站点列表（按租户隔离）"""
        query = select(CmsSite)
        conditions = [CmsSite.tenant_id == tenant_id]

        if not include_deleted:
            conditions.append(CmsSite.is_deleted == False)  # noqa: E712
        if status is not None:
            conditions.append(CmsSite.status == status)
        if keyword:
            conditions.append(
                or_(
                    CmsSite.name.ilike(f"%{keyword}%"),
                    CmsSite.code.ilike(f"%{keyword}%"),
                )
            )

        query = query.where(and_(*conditions))

        count_query = select(func.count(CmsSite.id)).where(and_(*conditions))
        total = await self.db.scalar(count_query)

        query = query.order_by(CmsSite.is_default.desc(), CmsSite.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def get_by_id(self, site_id: str) -> CmsSite | None:
        return await self.db.get(CmsSite, site_id)

    async def create(self, data: dict, tenant_id: str, operator_id: str | None = None) -> CmsSite:
        site = CmsSite(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=data["name"],
            code=data["code"],
            description=data.get("description"),
            domain=data.get("domain"),
            logo_url=data.get("logo_url"),
            favicon_url=data.get("favicon_url"),
            theme_config=_dump_json(data.get("theme_config")),
            seo_config=_dump_json(data.get("seo_config")),
            status=data.get("status", 1),
            is_default=data.get("is_default", 0),
        )
        set_create_audit(site, operator_id)
        self.db.add(site)
        await self.db.commit()
        await self.db.refresh(site)
        return site

    async def update(self, site_id: str, data: dict, operator_id: str | None = None) -> CmsSite | None:
        site = await self.get_by_id(site_id)
        if not site:
            return None

        for key, value in data.items():
            if not hasattr(site, key) or value is None:
                continue
            if key in ("theme_config", "seo_config") and value is not None:
                value = _dump_json(value)
            setattr(site, key, value)

        set_update_audit(site, operator_id)
        await self.db.commit()
        await self.db.refresh(site)
        return site

    async def delete(self, site_id: str) -> bool:
        site = await self.get_by_id(site_id)
        if not site or site.is_deleted:
            return False
        site.is_deleted = True
        site.deleted_at = datetime.now()
        set_update_audit(site)
        await self.db.commit()
        return True

    async def restore(self, site_id: str) -> bool:
        site = await self.get_by_id(site_id)
        if not site or not site.is_deleted:
            return False
        site.is_deleted = False
        site.deleted_at = None
        set_update_audit(site)
        await self.db.commit()
        return True

    async def permanent_delete(self, site_id: str) -> bool:
        site = await self.get_by_id(site_id)
        if not site:
            return False
        await self.db.delete(site)
        await self.db.commit()
        return True


# ============================================================
# 栏目服务（树形）
# ============================================================

class CmsCategoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        tenant_id: str,
        site_id: str | None = None,
        keyword: str | None = None,
        status: int | None = None,
        include_deleted: bool = False,
    ) -> list[CmsCategory]:
        """获取栏目列表（不分页，便于前端构建树）"""
        query = select(CmsCategory)
        conditions = [CmsCategory.tenant_id == tenant_id]

        if not include_deleted:
            conditions.append(CmsCategory.is_deleted == False)  # noqa: E712
        if site_id:
            conditions.append(CmsCategory.site_id == site_id)
        if status is not None:
            conditions.append(CmsCategory.status == status)
        if keyword:
            conditions.append(CmsCategory.name.ilike(f"%{keyword}%"))

        query = query.where(and_(*conditions))
        query = query.order_by(CmsCategory.sort_order.asc(), CmsCategory.created_at.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def build_tree(
        self,
        tenant_id: str,
        site_id: str | None = None,
        include_deleted: bool = False,
    ) -> list[dict]:
        """构建栏目树（嵌套结构）"""
        items = await self.get_list(
            tenant_id, site_id=site_id, include_deleted=include_deleted
        )
        nodes = {item.id: {"item": item, "children": []} for item in items}
        roots: list[dict] = []
        for item in items:
            node = nodes[item.id]
            if item.parent_id and item.parent_id in nodes:
                nodes[item.parent_id]["children"].append(node)
            else:
                roots.append(node)
        return roots

    async def get_by_id(self, category_id: str) -> CmsCategory | None:
        return await self.db.get(CmsCategory, category_id)

    async def create(self, data: dict, tenant_id: str, operator_id: str | None = None) -> CmsCategory:
        category = CmsCategory(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            site_id=data["site_id"],
            name=data["name"],
            slug=data["slug"],
            parent_id=data.get("parent_id"),
            sort_order=data.get("sort_order", 0),
            icon=data.get("icon"),
            description=data.get("description"),
            status=data.get("status", 1),
        )
        set_create_audit(category, operator_id)
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def update(self, category_id: str, data: dict, operator_id: str | None = None) -> CmsCategory | None:
        category = await self.get_by_id(category_id)
        if not category:
            return None
        for key, value in data.items():
            if hasattr(category, key) and value is not None:
                setattr(category, key, value)
        set_update_audit(category, operator_id)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def delete(self, category_id: str) -> bool:
        category = await self.get_by_id(category_id)
        if not category or category.is_deleted:
            return False
        category.is_deleted = True
        category.deleted_at = datetime.now()
        set_update_audit(category)
        await self.db.commit()
        return True

    async def batch_sort(self, items: list[dict]) -> int:
        """批量更新排序，返回更新数量"""
        updated = 0
        for it in items:
            category = await self.get_by_id(it["id"])
            if category:
                category.sort_order = it["sort_order"]
                updated += 1
        if updated:
            await self.db.commit()
        return updated


# ============================================================
# 文章服务
# ============================================================

class CmsArticleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        tenant_id: str,
        site_id: str | None = None,
        category_id: str | None = None,
        status: int | None = None,
        keyword: str | None = None,
        store_id: str | list[str] | None = None,
        page: int = 1,
        page_size: int = 10,
        include_deleted: bool = False,
        deleted_only: bool = False,
    ) -> tuple[list[CmsArticle], int]:
        """获取文章列表（租户隔离，可选门店过滤）

        - include_deleted=True: 返回全部（含已删除），用于跨状态统计
        - deleted_only=True: 仅返回回收站（已删除）文章
        - 默认: 仅返回未删除文章
        """
        query = select(CmsArticle)
        conditions = [CmsArticle.tenant_id == tenant_id]

        if deleted_only:
            conditions.append(CmsArticle.is_deleted == True)  # noqa: E712
        elif not include_deleted:
            conditions.append(CmsArticle.is_deleted == False)  # noqa: E712
        if site_id:
            conditions.append(CmsArticle.site_id == site_id)
        if category_id:
            conditions.append(CmsArticle.category_id == category_id)
        if status is not None:
            conditions.append(CmsArticle.status == status)
        if store_id:
            # 命中指定门店（单个或多个）或 站点级文章(store_id 为空)
            conditions.append(_store_condition(store_id))
        if keyword:
            conditions.append(
                or_(
                    CmsArticle.title.ilike(f"%{keyword}%"),
                    CmsArticle.summary.ilike(f"%{keyword}%"),
                )
            )

        query = query.where(and_(*conditions))
        count_query = select(func.count(CmsArticle.id)).where(and_(*conditions))
        total = await self.db.scalar(count_query)

        query = query.order_by(CmsArticle.is_top.desc(), CmsArticle.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def get_published(
        self,
        site_id: str,
        category_id: str | None = None,
        store_id: str | list[str] | None = None,
        limit: int = 10,
    ) -> list[CmsArticle]:
        """获取已发布文章（公开接口用）"""
        conditions = [CmsArticle.site_id == site_id, CmsArticle.status == 1, CmsArticle.is_deleted == False]  # noqa: E712
        if category_id:
            conditions.append(CmsArticle.category_id == category_id)
        if store_id:
            conditions.append(_store_condition(store_id))
        query = select(CmsArticle).where(and_(*conditions))
        query = query.order_by(CmsArticle.is_top.desc(), CmsArticle.publish_time.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, article_id: str) -> CmsArticle | None:
        return await self.db.get(CmsArticle, article_id)

    async def create(self, data: dict, tenant_id: str, operator_id: str | None = None) -> CmsArticle:
        article = CmsArticle(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            site_id=data["site_id"],
            store_id=data.get("store_id"),
            category_id=data.get("category_id"),
            title=data["title"],
            subtitle=data.get("subtitle"),
            slug=data.get("slug"),
            cover_image=data.get("cover_image"),
            summary=data.get("summary"),
            content=data.get("content"),
            author=data.get("author"),
            source=data.get("source"),
            tags=_dump_json(data.get("tags")),
            sort_order=data.get("sort_order", 0),
            is_top=data.get("is_top", 0),
            status=data.get("status", 0),
            publish_time=datetime.now() if data.get("status") == 1 else None,
            seo_title=data.get("seo_title"),
            seo_keywords=data.get("seo_keywords"),
            seo_description=data.get("seo_description"),
        )
        set_create_audit(article, operator_id)
        self.db.add(article)
        await self.db.commit()
        await self.db.refresh(article)
        return article

    async def update(self, article_id: str, data: dict, operator_id: str | None = None) -> CmsArticle | None:
        """更新文章（更新前保存版本快照到 content_versions）"""
        article = await self.get_by_id(article_id)
        if not article:
            return None

        # 保存版本快照
        snapshot = _make_snapshot(article)
        version = ContentVersion(
            id=str(uuid.uuid4()),
            content_type="cms_article",
            content_id=article_id,
            operator_id=operator_id,
            snapshot=json.dumps(snapshot, ensure_ascii=False),
        )
        self.db.add(version)

        for key, value in data.items():
            if not hasattr(article, key) or value is None:
                continue
            if key == "tags" and value is not None:
                value = _dump_json(value)
            setattr(article, key, value)

        # 发布时补发布时间
        if data.get("status") == 1 and not article.publish_time:
            article.publish_time = datetime.now()

        set_update_audit(article, operator_id)
        await self.db.commit()
        await self.db.refresh(article)
        return article

    async def delete(self, article_id: str) -> bool:
        article = await self.get_by_id(article_id)
        if not article or article.is_deleted:
            return False
        article.is_deleted = True
        article.deleted_at = datetime.now()
        set_update_audit(article)
        await self.db.commit()
        return True

    async def restore(self, article_id: str) -> bool:
        article = await self.get_by_id(article_id)
        if not article or not article.is_deleted:
            return False
        article.is_deleted = False
        article.deleted_at = None
        set_update_audit(article)
        await self.db.commit()
        return True

    async def permanent_delete(self, article_id: str) -> bool:
        article = await self.get_by_id(article_id)
        if not article:
            return False
        await self.db.delete(article)
        await self.db.commit()
        return True

    async def increment_view(self, article_id: str) -> None:
        article = await self.get_by_id(article_id)
        if article:
            article.view_count = (article.view_count or 0) + 1
            await self.db.commit()

    async def batch_delete(self, ids: list[str]) -> int:
        deleted_count = 0
        for article_id in ids:
            article = await self.get_by_id(article_id)
            if article and not article.is_deleted:
                article.is_deleted = True
                article.deleted_at = datetime.now()
                set_update_audit(article)
                deleted_count += 1
        if deleted_count:
            await self.db.commit()
        return deleted_count
