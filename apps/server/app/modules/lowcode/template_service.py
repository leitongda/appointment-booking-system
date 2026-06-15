"""低代码模板市场服务。"""

import asyncio
import copy
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lowcode_page import LowCodePage
from app.models.lowcode_template import LowCodeTemplate
from app.models.lowcode_template_version import LowCodeTemplateFork, LowCodeTemplateVersion
from app.utils.audit import set_create_audit, set_update_audit

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# codegen subprocess 配置 (与 codegen_service.py 保持一致)
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[5]  # monorepo root
_DEFAULT_CODEGEN_BIN = str(_PROJECT_ROOT / "packages" / "codegen" / "dist" / "index.js")


class LowCodeTemplateService:
    """低代码模板市场 CRUD 服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 1. 分页列出公开模板
    # ------------------------------------------------------------------
    async def list_templates(
        self,
        category: str | None = None,
        keyword: str | None = None,
        sort_by: str = "popular",
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict[str, Any]], int]:
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
    async def get_template(
        self, template_id: str, sanitize: bool = False
    ) -> dict[str, Any] | None:
        """获取单个模板详情，包含作者信息。

        Args:
            template_id: 模板 ID
            sanitize: 是否脱敏处理。为 True 时移除 schema_data 中 dataSources
                      的敏感字段 (url, headers)，保留 id, method, dataPath 等。
        """
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

        schema_data = t.schema_data
        if sanitize:
            schema_data = _sanitize_schema_data(schema_data)

        return {
            "id": str(t.id),
            "source_page_id": str(t.source_page_id) if t.source_page_id else None,
            "name": t.name,
            "description": t.description,
            "thumbnail_url": t.thumbnail_url,
            "category": t.category,
            "tags": t.tags or [],
            "schema_data": schema_data,
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
        description: str | None = None,
        thumbnail_url: str | None = None,
        tags: list[str] | None = None,
        is_public: bool = True,
        created_by: str | None = None,
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
        tenant_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        thumbnail_url: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        is_public: bool | None = None,
        updated_by: str | None = None,
    ) -> LowCodeTemplate | None:
        """更新模板元数据（不修改 schema）。

        Args:
            template_id: 模板 ID
            tenant_id: 当前租户 ID。传入时校验模板的 source_tenant_id
                       是否匹配，不匹配则拒绝更新。
        """
        query = select(LowCodeTemplate).where(
            LowCodeTemplate.id == template_id,
            LowCodeTemplate.status == 1,
        )
        result = await self.db.execute(query)
        template = result.scalar_one_or_none()
        if template is None:
            return None

        # 租户所有权校验：只有模板创建者才能更新
        if tenant_id and template.source_tenant_id != tenant_id:
            logger.warning(
                "租户 %s 尝试更新不属于自己的模板 %s (owner: %s)",
                tenant_id,
                template_id,
                template.source_tenant_id,
            )
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
    async def delete_template(
        self, template_id: str, tenant_id: str | None = None
    ) -> bool:
        """软删除模板（status=0）。

        Args:
            template_id: 模板 ID
            tenant_id: 当前租户 ID。传入时校验模板的 source_tenant_id
                       是否匹配，不匹配则拒绝删除。
        """
        query = select(LowCodeTemplate).where(
            LowCodeTemplate.id == template_id,
            LowCodeTemplate.status == 1,
        )
        result = await self.db.execute(query)
        template = result.scalar_one_or_none()
        if template is None:
            return False

        # 租户所有权校验
        if tenant_id is not None and template.source_tenant_id != tenant_id:
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
    ) -> tuple[list[LowCodeTemplate], int]:
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
    ) -> list[LowCodeTemplateVersion]:
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
        changelog: str | None = None,
        data_sources: dict[str, Any] | None = None,
        created_by: str | None = None,
    ) -> LowCodeTemplateVersion:
        """为模板创建新版本快照。

        在创建版本前，通过 codegen 的 analyzeSchema 校验 schema 兼容性。
        如果校验发现 error 级别的问题（如 INVALID_ROOT、MISSING_ID、
        DUPLICATE_ID、MISSING_COMPONENT_NAME），则抛出 ValueError。

        Args:
            template_id: 模板 ID
            version: 语义化版本号，如 "1.1.0"
            schema_data: 版本 schema 快照
            changelog: 变更说明
            data_sources: 数据源配置快照
            created_by: 创建人 ID

        Raises:
            ValueError: 模板不存在或 schema 校验失败时
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

        # 通过 codegen analyzeSchema 校验 schema 兼容性
        await self._validate_schema_with_codegen(schema_data)

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
    ) -> LowCodePage | None:
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

    @staticmethod
    async def _validate_schema_with_codegen(schema_data: dict[str, Any]) -> None:
        """调用 codegen analyzeSchema 校验 schema 兼容性。

        通过 subprocess 调用 Node.js codegen 包的 analyzeSchema 函数，
        将 error 级别的警告转换为 ValueError。

        Args:
            schema_data: 待校验的 schema 数据

        Raises:
            ValueError: 校验发现 error 级别问题时
        """
        codegen_bin = os.environ.get("CODEGEN_BIN", _DEFAULT_CODEGEN_BIN)
        node_cmd = os.environ.get("CODEGEN_NODE_CMD", "node")
        timeout = int(os.environ.get("CODEGEN_TIMEOUT", "30"))

        # 检查 codegen 入口是否存在
        if not Path(codegen_bin).exists():
            logger.warning(
                "codegen 未构建，跳过 schema 校验: %s", codegen_bin
            )
            return

        # 构造 analyzeSchema-only 的 Node.js 脚本
        input_data = {"schema": schema_data}
        input_json = json.dumps(input_data, ensure_ascii=False)

        analyze_script = """\
const fs = require('fs');
async function main() {
    const input = JSON.parse(fs.readFileSync(0, 'utf-8'));
    const codegenPath = process.argv[2];
    const codegen = require(codegenPath);
    if (!codegen.analyzeSchema) {
        process.stdout.write(JSON.stringify({ warnings: [] }));
        return;
    }
    const result = codegen.analyzeSchema(input.schema);
    process.stdout.write(JSON.stringify(result));
}
main().catch(function(err) {
    process.stderr.write(JSON.stringify({ error: err.message }));
    process.exit(1);
});
"""

        script_fd, script_path = tempfile.mkstemp(suffix=".js", prefix="codegen_analyze_")
        os.write(script_fd, analyze_script.encode("utf-8"))
        os.close(script_fd)

        try:
            proc = await asyncio.create_subprocess_exec(
                node_cmd,
                script_path,
                codegen_bin.replace("\\", "/"),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=input_json.encode("utf-8")),
                timeout=timeout,
            )
        except TimeoutError:
            proc.kill()
            await proc.wait()
            logger.warning("schema 校验超时 (%ds)，跳过", timeout)
            return
        except FileNotFoundError:
            logger.warning("node 命令不存在，跳过 schema 校验")
            return
        finally:
            try:
                os.unlink(script_path)
            except OSError:
                pass

        if proc.returncode != 0:
            stderr_text = stderr.decode("utf-8").strip() if stderr else ""
            logger.warning("schema 校验失败: %s", stderr_text)
            return

        stdout_text = stdout.decode("utf-8").strip()
        if not stdout_text:
            return

        try:
            output = json.loads(stdout_text)
        except json.JSONDecodeError:
            logger.warning("schema 校验输出非有效 JSON，跳过")
            return

        # 提取 error 级别的 warnings，如有则抛出 ValueError
        warnings = output.get("warnings", [])
        error_warnings = [
            w for w in warnings if w.get("severity") == "error"
        ]
        if error_warnings:
            messages = [w.get("message", "unknown error") for w in error_warnings]
            raise ValueError(
                "Schema 校验失败: " + "; ".join(messages)
            )


# ---------------------------------------------------------------------------
# 模块级脱敏辅助函数
# ---------------------------------------------------------------------------

# dataSources 中需要移除的敏感字段
_SENSITIVE_DS_FIELDS = {"url", "headers"}


def _sanitize_schema_data(schema_data: dict[str, Any]) -> dict[str, Any]:
    """递归脱敏 schema_data，移除 dataSources 中的敏感字段。

    移除 dataSources 列表中每个数据源的 url 和 headers 字段，
    保留 id、method、dataPath 等非敏感字段。

    Args:
        schema_data: 原始 schema 数据

    Returns:
        脱敏后的 schema 数据副本
    """
    if not schema_data:
        return schema_data

    sanitized = copy.deepcopy(schema_data)

    # 处理顶层 dataSources
    if "dataSources" in sanitized and isinstance(sanitized["dataSources"], list):
        sanitized["dataSources"] = [
            _sanitize_datasource(ds) for ds in sanitized["dataSources"]
        ]

    # 递归处理组件树中的节点级 api 声明
    _sanitize_node_tree(sanitized.get("children", []))

    return sanitized


def _sanitize_datasource(ds: dict[str, Any]) -> dict[str, Any]:
    """移除单个数据源的敏感字段。"""
    if not isinstance(ds, dict):
        return ds
    return {k: v for k, v in ds.items() if k not in _SENSITIVE_DS_FIELDS}


def _sanitize_node_tree(nodes: Any) -> None:
    """递归遍历组件树，脱敏节点级别的 api 声明。"""
    if not isinstance(nodes, list):
        return
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if "api" in node and isinstance(node["api"], dict):
            node["api"] = _sanitize_datasource(node["api"])
        if "children" in node:
            _sanitize_node_tree(node["children"])
