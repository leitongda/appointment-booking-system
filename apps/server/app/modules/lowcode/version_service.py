"""低代码页面版本管理服务。"""

from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lowcode_page import LowCodePage
from app.models.lowcode_page_version import LowCodePageVersion
from app.utils.audit import set_create_audit


class LowCodePageVersionService:
    """低代码页面版本快照与回滚服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 1. 创建版本快照
    # ------------------------------------------------------------------
    async def create_snapshot(
        self,
        page_id: str,
        tenant_id: str,
        label: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> LowCodePageVersion:
        """创建页面版本快照。

        加载 LowCodePage 当前 schema_data，自增版本号，
        生成 LowCodePageVersion 记录并更新页面的
        current_version 和 publish_count。
        """
        # 加载页面
        page = await self._get_page(page_id, tenant_id)
        if page is None:
            raise ValueError(f"页面不存在: {page_id}")

        # 计算新版本号
        latest_version = await self._get_max_version(page_id)
        new_version = latest_version + 1

        # 创建版本记录
        version_record = LowCodePageVersion(
            page_id=page_id,
            tenant_id=tenant_id,
            version=new_version,
            schema_data=page.schema_data or {},
            data_sources=(page.schema_data or {}).get("dataSources", []),
            snapshot_label=label,
        )
        set_create_audit(version_record, created_by)
        self.db.add(version_record)

        # 更新页面版本计数
        page.current_version = new_version
        page.publish_count = (page.publish_count or 0) + 1

        await self.db.commit()
        await self.db.refresh(version_record)
        return version_record

    # ------------------------------------------------------------------
    # 2. 列出页面所有版本
    # ------------------------------------------------------------------
    async def get_versions(
        self, page_id: str, tenant_id: str
    ) -> List[LowCodePageVersion]:
        """按版本号降序列出页面的所有版本记录。"""
        query = (
            select(LowCodePageVersion)
            .where(
                LowCodePageVersion.page_id == page_id,
                LowCodePageVersion.tenant_id == tenant_id,
            )
            .order_by(LowCodePageVersion.version.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # 3. 获取单个版本
    # ------------------------------------------------------------------
    async def get_version(self, version_id: str) -> Optional[LowCodePageVersion]:
        """根据版本记录 ID 获取单个版本。"""
        query = select(LowCodePageVersion).where(
            LowCodePageVersion.id == version_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # 4. 回滚到指定版本
    # ------------------------------------------------------------------
    async def rollback_to_version(
        self,
        page_id: str,
        version_id: str,
        tenant_id: str,
    ) -> LowCodePage:
        """将页面回滚到指定历史版本。

        读取目标版本的 schema_data，更新页面，
        同时创建一条新的版本记录（版本号 +1），
        label 标记为 "回滚至 v{x}"。
        """
        # 校验页面存在
        page = await self._get_page(page_id, tenant_id)
        if page is None:
            raise ValueError(f"页面不存在: {page_id}")

        # 校验目标版本存在且属于该页面
        target_version = await self.get_version(version_id)
        if (
            target_version is None
            or target_version.page_id != page_id
            or target_version.tenant_id != tenant_id
        ):
            raise ValueError(f"版本不存在: {version_id}")

        # 更新页面 schema_data 为目标版本的快照
        page.schema_data = target_version.schema_data

        # 创建新版本记录（回滚也会生成版本历史）
        latest_version = await self._get_max_version(page_id)
        new_version = latest_version + 1

        rollback_record = LowCodePageVersion(
            page_id=page_id,
            tenant_id=tenant_id,
            version=new_version,
            schema_data=target_version.schema_data,
            data_sources=target_version.data_sources or [],
            snapshot_label=f"回滚至 v{target_version.version}",
        )
        set_create_audit(rollback_record, None)
        self.db.add(rollback_record)

        # 更新页面版本号和发布次数
        page.current_version = new_version
        page.publish_count = (page.publish_count or 0) + 1

        await self.db.commit()
        await self.db.refresh(page)
        return page

    # ------------------------------------------------------------------
    # 5. 获取最新版本
    # ------------------------------------------------------------------
    async def get_latest_version(
        self, page_id: str
    ) -> Optional[LowCodePageVersion]:
        """获取页面最新一条版本记录（版本号最大的那条）。"""
        query = (
            select(LowCodePageVersion)
            .where(LowCodePageVersion.page_id == page_id)
            .order_by(LowCodePageVersion.version.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    async def _get_page(
        self, page_id: str, tenant_id: str
    ) -> Optional[LowCodePage]:
        query = select(LowCodePage).where(
            LowCodePage.id == page_id,
            LowCodePage.tenant_id == tenant_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_max_version(self, page_id: str) -> int:
        """获取页面当前最大版本号，无记录时返回 0。"""
        query = select(func.coalesce(func.max(LowCodePageVersion.version), 0)).where(
            LowCodePageVersion.page_id == page_id
        )
        result = await self.db.execute(query)
        return result.scalar() or 0
