"""知识库服务：知识库 CRUD + 目录树（文档/共享见 service_documents；级别判定见 service_access）"""
import uuid

from sqlalchemy import delete, func, select

from app.core.logging import logger
from app.enums.knowledge import KnowledgeVisibility
from app.infrastructure.embedding import get_embedding_config
from app.infrastructure.storage import get_storage
from app.models.knowledge import (
    KnowledgeBase,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeFolder,
    KnowledgeShare,
)
from app.modules.knowledge.exceptions import KnowledgeConflict
from app.modules.knowledge.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeFolderCreate,
    KnowledgeFolderUpdate,
)
from app.modules.knowledge.service_base import (  # noqa: F401 — 兼容从 service 导入辅助函数
    KnowledgeServiceBase,
    refresh_kb_counts,
    resolve_local_file,
    validate_upload_file,
)


class KnowledgeService(KnowledgeServiceBase):
    # ==================== 知识库 ====================

    async def list_bases(
        self,
        scope: str = "all",
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[KnowledgeBase], int]:
        visible = await self.access.visible_kb_ids()
        if visible is not None and not visible:
            return [], 0

        stmt = self._scoped(select(KnowledgeBase), KnowledgeBase)
        if visible is not None:
            stmt = stmt.where(KnowledgeBase.id.in_(visible))
        if scope == "mine":
            stmt = stmt.where(KnowledgeBase.owner_admin_id == self.admin_id)
        elif scope == "shared":
            stmt = stmt.where(
                KnowledgeBase.owner_admin_id != self.admin_id,
                KnowledgeBase.id.in_(await self.access.shared_kb_ids_subquery()),
            )
        elif scope == "tenant":
            stmt = stmt.where(
                KnowledgeBase.visibility == KnowledgeVisibility.TENANT.value,
                KnowledgeBase.owner_admin_id != self.admin_id,
            )
        if keyword:
            stmt = stmt.where(KnowledgeBase.name.ilike(f"%{keyword.strip()}%"))

        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = (
            await self.db.execute(
                stmt.order_by(KnowledgeBase.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
            )
        ).scalars().all()
        return list(rows), total

    async def create_base(self, data: KnowledgeBaseCreate) -> KnowledgeBase:
        embedding = get_embedding_config()
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            tenant_id=self.tenant_id,
            name=data.name.strip(),
            description=data.description,
            owner_admin_id=self.admin_id,
            visibility=data.visibility.value,
            embedding_model=embedding.model,
            embedding_dims=embedding.dims,
            created_by=self.admin_id,
        )
        self.db.add(kb)
        await self.db.commit()
        await self.db.refresh(kb)
        return kb

    async def update_base(self, kb_id: str, data: KnowledgeBaseUpdate) -> KnowledgeBase:
        kb, _ = await self.get_base(kb_id, "owner")
        fields = data.model_fields_set
        if "name" in fields and data.name is not None:
            kb.name = data.name.strip()
        if "description" in fields:
            kb.description = data.description
        if "visibility" in fields and data.visibility is not None:
            kb.visibility = data.visibility.value
        kb.updated_by = self.admin_id
        await self.db.commit()
        await self.db.refresh(kb)
        return kb

    async def delete_base(self, kb_id: str) -> None:
        kb, _ = await self.get_base(kb_id, "owner")
        docs = (
            await self.db.execute(select(KnowledgeDocument).where(KnowledgeDocument.kb_id == kb.id))
        ).scalars().all()
        storage = get_storage()
        for doc in docs:
            try:
                await storage.delete(doc.file_key)
            except Exception as exc:
                logger.warning(f"[knowledge] 删除原件失败 doc={doc.id}: {type(exc).__name__}")

        await self.db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.kb_id == kb.id))
        await self.db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.kb_id == kb.id))
        await self.db.execute(delete(KnowledgeShare).where(KnowledgeShare.kb_id == kb.id))
        await self.db.execute(delete(KnowledgeFolder).where(KnowledgeFolder.kb_id == kb.id))
        await self.db.delete(kb)
        await self.db.commit()

    # ==================== 目录 ====================

    async def list_folders(self, kb_id: str) -> list[KnowledgeFolder]:
        kb, _ = await self.get_base(kb_id, "read")
        stmt = (
            select(KnowledgeFolder)
            .where(KnowledgeFolder.kb_id == kb.id)
            .order_by(KnowledgeFolder.sort_order, KnowledgeFolder.name)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def _ensure_folder_name_unique(
        self, kb_id: str, parent_id: str | None, name: str, exclude_id: str | None = None
    ) -> None:
        stmt = select(KnowledgeFolder.id).where(KnowledgeFolder.kb_id == kb_id, KnowledgeFolder.name == name)
        if parent_id is None:
            stmt = stmt.where(KnowledgeFolder.parent_id.is_(None))
        else:
            stmt = stmt.where(KnowledgeFolder.parent_id == parent_id)
        if exclude_id:
            stmt = stmt.where(KnowledgeFolder.id != exclude_id)
        if (await self.db.execute(stmt)).first() is not None:
            raise KnowledgeConflict("同级目录下已存在同名目录")

    async def _is_descendant(self, candidate_id: str, ancestor_id: str) -> bool:
        """candidate 是否位于 ancestor 的子树内（含自身）"""
        current_id: str | None = candidate_id
        for _ in range(100):
            if current_id is None:
                return False
            if current_id == ancestor_id:
                return True
            current_id = (
                await self.db.execute(select(KnowledgeFolder.parent_id).where(KnowledgeFolder.id == current_id))
            ).scalar_one_or_none()
        return False

    async def create_folder(self, kb_id: str, data: KnowledgeFolderCreate) -> KnowledgeFolder:
        kb, _ = await self.get_base(kb_id, "edit")
        if data.parent_id:
            await self._load_folder_in_kb(data.parent_id, kb.id)
        name = data.name.strip()
        await self._ensure_folder_name_unique(kb.id, data.parent_id or None, name)
        folder = KnowledgeFolder(
            id=str(uuid.uuid4()),
            tenant_id=self.tenant_id,
            kb_id=kb.id,
            parent_id=data.parent_id or None,
            name=name,
            sort_order=data.sort_order,
            created_by=self.admin_id,
        )
        self.db.add(folder)
        await self.db.commit()
        await self.db.refresh(folder)
        return folder

    async def update_folder(self, folder_id: str, data: KnowledgeFolderUpdate) -> KnowledgeFolder:
        folder = await self._load_folder(folder_id)
        kb, _ = await self.get_base(folder.kb_id, "edit")
        fields = data.model_fields_set

        new_parent_id = folder.parent_id
        if "parent_id" in fields:
            if data.parent_id == folder.id:
                raise KnowledgeConflict("不能移动到自身")
            if data.parent_id:
                await self._load_folder_in_kb(data.parent_id, kb.id)
                if await self._is_descendant(data.parent_id, folder.id):
                    raise KnowledgeConflict("不能移动到自己的子目录")
            new_parent_id = data.parent_id or None

        new_name = data.name.strip() if data.name is not None else folder.name
        if new_parent_id != folder.parent_id or new_name != folder.name:
            await self._ensure_folder_name_unique(kb.id, new_parent_id, new_name, exclude_id=folder.id)

        folder.parent_id = new_parent_id
        folder.name = new_name
        if data.sort_order is not None:
            folder.sort_order = data.sort_order
        folder.updated_by = self.admin_id
        await self.db.commit()
        await self.db.refresh(folder)
        return folder

    async def delete_folder(self, folder_id: str) -> None:
        folder = await self._load_folder(folder_id)
        await self.get_base(folder.kb_id, "edit")
        child_count = (
            await self.db.execute(select(func.count(KnowledgeFolder.id)).where(KnowledgeFolder.parent_id == folder.id))
        ).scalar_one()
        doc_count = (
            await self.db.execute(
                select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.folder_id == folder.id)
            )
        ).scalar_one()
        if child_count or doc_count:
            raise KnowledgeConflict("目录非空，请先移走或删除其中的内容")
        await self.db.delete(folder)
        await self.db.commit()
