"""低代码模板市场服务。"""

import time
from typing import Any, List, Optional, Tuple

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lowcode_page import LowCodePage
from app.models.lowcode_template import LowCodeTemplate
from app.models.lowcode_template_version import LowCodeTemplateFork, LowCodeTemplateVersion
from app.utils.audit import set_create_audit, set_update_audit


class LowCodeTemplateService:
    """低代码模板市场 CRUD 服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 1. 分页列出公开模板
    # ------------------------------------------------------------------
    async def list_templates(
        self,
        category: Optional[str] = None,
        keyword: Optional[str] = None,
        sort_by: str = "popular",
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[dict[str, Any]], int]:
        """分页列出公开模板，支持分类筛选、全文搜索、排序。

        Args:
            category: 模板分类筛选
            keyword: 按名称或描述全文搜索
            sort_by: 排序方式 -- popular(下载量) | newest(创建时间) | forks(Fork数)
            page: 页码，从 1 开始
            page_size: 每页条数

        Returns:
            (模板列表, 总数)
        """
        base_filter = and_(
            LowCodeTemplate.is_public == True,  # noqa: E712
            LowCodeTemplate.status == 1,
        )

        conditions = [base_filter]

        if category:
            conditions.append(LowCodeTemplate.category == category)
        if keyword:
            search = f"%{keyword}%"
            conditions.append(
                or_(
                    LowCodeTemplate.name.ilike(search),
                    LowCodeTemplate.description.ilike(search),
                )
            )

        where = and_(*conditions)

        # 总数
        count_q = select(func.count(LowCodeTemplate.id)).where(where)
        total = await self.db.scalar(count_q) or 0

        # 排序
        order_map = {
            "popular": LowCodeTemplate.download_count.desc(),
            "newest": LowCodeTemplate.created_at.desc(),
            "forks": LowCodeTemplate.fork_count.desc(),
        }
        order = order_map.get(sort_by, order_map["popular"])

        query = (
            select(LowCodeTemplate)
            .where(where)
            .order_by(order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        items = result.scalars().all()

        # 组装作者信息（内联查询避免 N+1）
        author_ids = {t.created_by for t in items if t.created_by}
        author_map = await self._batch_get_author_names(author_ids)

        data: list[dict[str, Any]] = []
        for t in items:
            data.append(
                {
                    "id": str(t.id),
                    "name": t.name,
                    "description": t.description,
                    "thumbnail_url": t.thumbnail_url,
                    "category": t.category,
                    "tags": t.tags or [],
                    "version": t.version,
                    "is_official": t.is_official,
                    "download_count": t.download_count,
                    "fork_count": t.fork_count,
                    "like_count": t.like_count,
                    "author_id": str(t.created_by) if t.created_by else None,
                    "author_name": author_map.get(str(t.created_by), ""),
                    "created_at": t.created_at,
                }
            )

        return data, total

    # ------------------------------------------------------------------
    # 2. 获取模板详情（含作者信息）
    # ------------------------------------------------------------------
    async def get_template(self, template_id: str) -> Optional[dict[str, Any]]:
        """获取单个模板详情，包含作者信息。"""
        query = select(LowCodeTemplate).where(
            LowCodeTemplate.id == template_id,
            LowCodeTemplate.status == 1,
        )
        result = await self.db.execute(query)
        t = result.scalar_one_or_none()
        if t is None:
            return None

        author_name = ""
        if t.created_by:
            author_map = await self._batch_get_author_names({str(t.created_by)})
            author_name = author_map.get(str(t.created_by), "")

        return {
            "id": str(t.id),
            "source_page_id": str(t.source_page_id) if t.source_page_id else None,
            "name": t.name,
            "description": t.description,
            "thumbnail_url": t.thumbnail_url,
            "category": t.category,
            "tags": t.tags or [],
            "schema_data": t.schema_data,
            "data_sources": t.data_sources or [],
            "version": t.version,
            "is_public": t.is_public,
            "is_official": t.is_official,
            "download_count": t.download_count,
            "fork_count": t.fork_count,
            "like_count": t.like_count,
            "author_id": str(t.created_by) if t.created_by else None,
            "author_name": author_name,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
        }

    # ------------------------------------------------------------------
    # 3. 从页面创建模板
    # ------------------------------------------------------------------
    async def create_template(
        self,
        source_page_id: str,
        tenant_id: str,
        name: str,
        category: str,
        description: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        tags: Optional[list[str]] = None,
        is_public: bool = True,
        created_by: Optional[str] = None,
    ) -> LowCodeTemplate:
        """从已有页面创建模板（复制 schema_data）。

        Args:
            source_page_id: 来源页面 ID
            tenant_id: 来源租户 ID
            name: 模板名称
            category: 模板分类
            description: 模板描述
            thumbnail_url: 缩略图 URL
            tags: 标签列表
            is_public: 是否公开到市场
            created_by: 创建人 ID
        """
        # 加载来源页面，复制 schema
        page = await self._get_page(source_page_id, tenant_id)
        if page is None:
            raise ValueError(f"页面不存在: {source_page_id}")

        template = LowCodeTemplate(
            source_page_id=source_page_id,
            source_tenant_id=tenant_id,
            name=name,
            description=description,
            thumbnail_url=thumbnail_url,
            category=category,
            tags=tags or [],
            schema_data=page.schema_data or {},
            data_sources=(page.schema_data or {}).get("dataSources", []),
            version="1.0.0",
            is_public=is_public,
        )
        set_create_audit(template, created_by)
        self.db.add(template)

        # 同时创建初始版本记录
        initial_version = LowCodeTemplateVersion(
            version="1.0.0",
            schema_data=page.schema_data or {},
            data_sources=(page.schema_data or {}).get("dataSources", []),
            changelog="初始版本",
            status=2,  # 已发布
        )
        set_create_audit(initial_version, created_by)
        self.db.add(initial_version)

        await self.db.commit()
        await self.db.refresh(template)

        # 关联 template_id 到版本记录
        initial_version.template_id = template.id
        await self.db.commit()
        await self.db.refresh(initial_version)

        return template

    # ------------------------------------------------------------------
    # 4. 更新模板元数据
    # ------------------------------------------------------------------
    async def update_template(
        self,
        template_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        is_public: Optional[bool] = None,
        updated_by: Optional[str] = None,
    ) -> Optional[LowCodeTemplate]:
        """更新模板元数据（不修改 schema）。"""
        query = select(LowCodeTemplate).where(
            LowCodeTemplate.id == template_id,
            LowCodeTemplate.status == 1,
        )
        result = await self.db.execute(query)
        template = result.scalar_one_or_none()
        if template is None:
            return None

        if name is not None:
            template.name = name
        if description is not None:
            template.description = description
        if thumbnail_url is not None:
            template.thumbnail_url = thumbnail_url
        if category is not None:
            template.category = category
        if tags is not None:
            template.tags = tags
        if is_public is not None:
            template.is_public = is_public

        set_update_audit(template, updated_by)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    # ------------------------------------------------------------------
    # 5. 软删除模板
    # ------------------------------------------------------------------
    async def delete_template(self, template_id: str) -> bool:
        """软删除模板（status=0）。"""
        query = select(LowCodeTemplate).where(
            LowCodeTemplate.id == template_id,
            LowCodeTemplate.status == 1,
        )
        result = await self.db.execute(query)
        template = result.scalar_one_or_none()
        if template is None:
            return False

        template.status = 0
        await self.db.commit()
        return True

    # ------------------------------------------------------------------
    # 6. Fork 模板
    # ------------------------------------------------------------------
    async def fork_template(
        self,
        template_id: str,
        tenant_id: str,
        account_id: str,
        name: str | None = None,
        slug: str | None = None,
    ) -> LowCodePage:
        """Fork 模板：基于模板 schema 创建新页面，记录 fork，递增 fork_count。"""
        # 加载模板
        query = select(LowCodeTemplate).where(
            LowCodeTemplate.id == template_id,
            LowCodeTemplate.status == 1,
        )
        result = await self.db.execute(query)
        template = result.scalar_one_or_none()
        if template is None:
            raise ValueError(f"模板不存在: {template_id}")

        # 使用传入的 name/slug, 否则回退到默认值
        page_name = name if name else f"{template.name} (Fork)"
        page_slug = slug if slug else f"fork-{template_id[:8]}"

        # 创建新页面，复制 schema_data
        page = LowCodePage(
            tenant_id=tenant_id,
            name=page_name,
            slug=page_slug,
            description=template.description,
            schema_data=template.schema_data or {},
            thumbnail_url=template.thumbnail_url,
        )
        set_create_audit(page, account_id)
        self.db.add(page)
        await self.db.flush()  # 获取 page.id

        # 记录 fork
        fork = LowCodeTemplateFork(
            original_template_id=template_id,
            forked_page_id=page.id,
            forked_by_tenant_id=tenant_id,
            forked_by_account_id=account_id,
            created_at=int(time.time()),
        )
        self.db.add(fork)

        # 递增 fork_count 和 download_count
        template.fork_count = (template.fork_count or 0) + 1
        template.download_count = (template.download_count or 0) + 1

        await self.db.commit()
        await self.db.refresh(page)
        return page

    # ------------------------------------------------------------------
    # 7. 获取当前租户发布的模板
    # ------------------------------------------------------------------
    async def get_my_templates(
        self,
        tenant_id: str,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[LowCodeTemplate], int]:
        """列出当前租户发布的所有模板（含已下架）。"""
        where = LowCodeTemplate.source_tenant_id == tenant_id

        count_q = select(func.count(LowCodeTemplate.id)).where(where)
        total = await self.db.scalar(count_q) or 0

        query = (
            select(LowCodeTemplate)
            .where(where)
            .order_by(LowCodeTemplate.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total

    # ------------------------------------------------------------------
    # 8. 获取模板版本列表
    # ------------------------------------------------------------------
    async def get_template_versions(
        self, template_id: str
    ) -> List[LowCodeTemplateVersion]:
        """按版本号降序列出模板的所有版本记录。"""
        query = (
            select(LowCodeTemplateVersion)
            .where(LowCodeTemplateVersion.template_id == template_id)
            .order_by(LowCodeTemplateVersion.version.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # 9. 创建新版本
    # ------------------------------------------------------------------
    async def create_version(
        self,
        template_id: str,
        version: str,
        schema_data: dict[str, Any],
        changelog: Optional[str] = None,
        data_sources: Optional[dict[str, Any]] = None,
        created_by: Optional[str] = None,
    ) -> LowCodeTemplateVersion:
        """为模板创建新版本快照。

        Args:
            template_id: 模板 ID
            version: 语义化版本号，如 "1.1.0"
            schema_data: 版本 schema 快照
            changelog: 变更说明
            data_sources: 数据源配置快照
            created_by: 创建人 ID
        """
        # 校验模板存在
        query = select(LowCodeTemplate).where(
            LowCodeTemplate.id == template_id,
            LowCodeTemplate.status == 1,
        )
        result = await self.db.execute(query)
        template = result.scalar_one_or_none()
        if template is None:
            raise ValueError(f"模板不存在: {template_id}")

        version_record = LowCodeTemplateVersion(
            template_id=template_id,
            version=version,
            schema_data=schema_data,
            data_sources=data_sources or {},
            changelog=changelog,
            status=2,  # 已发布
        )
        set_create_audit(version_record, created_by)
        self.db.add(version_record)

        # 同步更新模板主版本号
        template.version = version
        template.schema_data = schema_data

        await self.db.commit()
        await self.db.refresh(version_record)
        return version_record

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    async def _get_page(
        self, page_id: str, tenant_id: str
    ) -> Optional[LowCodePage]:
        """根据 ID 和租户加载页面。"""
        query = select(LowCodePage).where(
            LowCodePage.id == page_id,
            LowCodePage.tenant_id == tenant_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _batch_get_author_names(
        self, author_ids: set[str]
    ) -> dict[str, str]:
        """批量获取创建人显示名称（Account 表）。"""
        if not author_ids:
            return {}

        from app.models.account import Account

        query = select(Account.id, Account.username).where(
            Account.id.in_(list(author_ids))
        )
        result = await self.db.execute(query)
        return {str(row[0]): row[1] or "" for row in result.all()}
