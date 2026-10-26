"""知识库服务：文档（上传/重试/下载/切片）+ 共享授权（知识库/目录见 service）"""
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import delete, func, select

from app.common.quota import check_quota
from app.core.config import settings
from app.core.logging import logger
from app.enums.knowledge import KnowledgeDocStatus, KnowledgeShareGrantee
from app.infrastructure.storage import get_storage
from app.infrastructure.storage.base import build_tenant_storage_folder
from app.models.admin import Admin, Role
from app.models.knowledge import (
    KnowledgeBase,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeShare,
)
from app.modules.knowledge import service_base
from app.modules.knowledge.exceptions import KnowledgeConflict, KnowledgeNotFound
from app.modules.knowledge.schemas import KnowledgeDocumentUpdate, KnowledgeShareCreate
from app.modules.knowledge.service_base import (
    KnowledgeServiceBase,
    refresh_kb_counts,
    resolve_local_file,
    validate_upload_file,
)


class KnowledgeDocumentService(KnowledgeServiceBase):
    # ==================== 文档 ====================

    async def list_documents(
        self,
        kb_id: str,
        folder_id: str | None = None,
        root_only: bool = False,
        status: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[KnowledgeDocument], int]:
        kb, _ = await self.get_base(kb_id, "read")
        stmt = select(KnowledgeDocument).where(KnowledgeDocument.kb_id == kb.id)
        if folder_id:
            stmt = stmt.where(KnowledgeDocument.folder_id == folder_id)
        elif root_only:
            stmt = stmt.where(KnowledgeDocument.folder_id.is_(None))
        if status:
            stmt = stmt.where(KnowledgeDocument.status == status)
        if keyword:
            pattern = f"%{keyword.strip()}%"
            stmt = stmt.where(KnowledgeDocument.title.ilike(pattern) | KnowledgeDocument.file_name.ilike(pattern))

        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = (
            await self.db.execute(
                stmt.order_by(KnowledgeDocument.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
            )
        ).scalars().all()
        return list(rows), total

    async def upload_document(
        self,
        kb_id: str,
        upload: UploadFile,
        folder_id: str | None = None,
        title: str | None = None,
    ) -> KnowledgeDocument:
        kb, _ = await self.get_base(kb_id, "edit")
        if folder_id:
            await self._load_folder_in_kb(folder_id, kb.id)

        filename = upload.filename or "untitled"
        upload.file.seek(0, 2)
        size_bytes = upload.file.tell()
        upload.file.seek(0)
        _, mime_type = validate_upload_file(filename, size_bytes)
        await check_quota(self.tenant_id, "storage_mb", self.db)

        doc_id = str(uuid.uuid4())
        folder_key = build_tenant_storage_folder(f"knowledge/{kb.id}/{doc_id}", self.tenant_id)
        result = await get_storage().upload(
            file=upload.file,
            filename=filename,
            content_type=mime_type,
            folder=folder_key,
        )

        default_title = filename.rsplit(".", 1)[0] if "." in filename else filename
        doc = KnowledgeDocument(
            id=doc_id,
            tenant_id=self.tenant_id,
            kb_id=kb.id,
            folder_id=folder_id or None,
            title=((title or "").strip() or default_title)[:200],
            file_name=filename[:255],
            file_key=result.key,
            mime_type=mime_type,
            size_bytes=size_bytes,
            status=KnowledgeDocStatus.PENDING.value,
            uploaded_by=self.admin_id,
            created_by=self.admin_id,
        )
        self.db.add(doc)
        await self.db.flush()
        await refresh_kb_counts(self.db, kb.id)
        await self.db.commit()
        await self.db.refresh(doc)

        service_base.enqueue_process_document(doc.id)
        logger.info(f"[knowledge] 文档已上传并投递 doc={doc.id} kb={kb.id} size={size_bytes}")
        return doc

    async def get_document(self, doc_id: str, level: str = "read") -> tuple[KnowledgeDocument, KnowledgeBase]:
        stmt = self._scoped(select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id), KnowledgeDocument)
        doc = (await self.db.execute(stmt)).scalar_one_or_none()
        if doc is None:
            raise KnowledgeNotFound("文档不存在")
        kb, _ = await self.get_base(doc.kb_id, level)
        return doc, kb

    async def update_document(self, doc_id: str, data: KnowledgeDocumentUpdate) -> KnowledgeDocument:
        doc, kb = await self.get_document(doc_id, "edit")
        fields = data.model_fields_set
        if "title" in fields and data.title is not None:
            doc.title = data.title.strip()[:200]
        if "folder_id" in fields:
            if data.folder_id:
                await self._load_folder_in_kb(data.folder_id, kb.id)
            doc.folder_id = data.folder_id or None
        doc.updated_by = self.admin_id
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def delete_document(self, doc_id: str) -> None:
        doc, kb = await self.get_document(doc_id, "edit")
        await self.db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.doc_id == doc.id))
        try:
            await get_storage().delete(doc.file_key)
        except Exception as exc:
            logger.warning(f"[knowledge] 删除原件失败 doc={doc.id}: {type(exc).__name__}")
        await self.db.delete(doc)
        await self.db.flush()
        await refresh_kb_counts(self.db, kb.id)
        await self.db.commit()

    async def retry_document(self, doc_id: str) -> KnowledgeDocument:
        doc, _ = await self.get_document(doc_id, "edit")
        if doc.status != KnowledgeDocStatus.FAILED.value:
            raise KnowledgeConflict("仅失败的文档可重新处理")
        doc.status = KnowledgeDocStatus.PENDING.value
        doc.failed_stage = None
        doc.error_message = None
        doc.updated_by = self.admin_id
        await self.db.commit()
        await self.db.refresh(doc)
        service_base.enqueue_process_document(doc.id)
        return doc

    async def list_chunks(self, doc_id: str, page: int = 1, page_size: int = 20) -> tuple[list[KnowledgeChunk], int]:
        doc, _ = await self.get_document(doc_id, "read")
        stmt = select(KnowledgeChunk).where(KnowledgeChunk.doc_id == doc.id)
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = (
            await self.db.execute(stmt.order_by(KnowledgeChunk.seq).offset((page - 1) * page_size).limit(page_size))
        ).scalars().all()
        return list(rows), total

    async def resolve_document_file(self, doc_id: str) -> tuple[KnowledgeDocument, Path | None, str | None]:
        """返回 (doc, 本地路径, 远端 URL)：local 存储给路径，其他存储给可直接重定向的 URL"""
        doc, _ = await self.get_document(doc_id, "read")
        if settings.STORAGE_TYPE.lower() == "local":
            path = resolve_local_file(doc.file_key)
            if path is None:
                raise KnowledgeNotFound("文件不存在")
            return doc, path, None
        return doc, None, await get_storage().get_url(doc.file_key)

    # ==================== 共享 ====================

    async def list_shares(self, kb_id: str) -> list[tuple[KnowledgeShare, str | None]]:
        kb, _ = await self.get_base(kb_id, "owner")
        shares = list(
            (
                await self.db.execute(
                    select(KnowledgeShare).where(KnowledgeShare.kb_id == kb.id).order_by(KnowledgeShare.created_at)
                )
            ).scalars().all()
        )
        names = await self._grantee_names(shares)
        return [(share, names.get((share.grantee_type, share.grantee_id))) for share in shares]

    async def _grantee_names(self, shares: list[KnowledgeShare]) -> dict[tuple[str, str], str]:
        admin_ids = [s.grantee_id for s in shares if s.grantee_type == KnowledgeShareGrantee.ADMIN.value]
        role_ids = [s.grantee_id for s in shares if s.grantee_type == KnowledgeShareGrantee.ROLE.value]
        names: dict[tuple[str, str], str] = {}
        if admin_ids:
            rows = await self.db.execute(select(Admin.id, Admin.name, Admin.username).where(Admin.id.in_(admin_ids)))
            for admin_id, name, username in rows.all():
                names[(KnowledgeShareGrantee.ADMIN.value, admin_id)] = name or username
        if role_ids:
            rows = await self.db.execute(select(Role.id, Role.name).where(Role.id.in_(role_ids)))
            for role_id, name in rows.all():
                names[(KnowledgeShareGrantee.ROLE.value, role_id)] = name
        return names

    async def add_share(self, kb_id: str, data: KnowledgeShareCreate) -> tuple[KnowledgeShare, str | None]:
        kb, _ = await self.get_base(kb_id, "owner")

        if data.grantee_type == KnowledgeShareGrantee.ADMIN:
            if data.grantee_id in (self.admin_id, kb.owner_admin_id):
                raise KnowledgeConflict("不能共享给知识库拥有者自己")
            stmt = self._scoped(select(Admin).where(Admin.id == data.grantee_id), Admin)
            admin = (await self.db.execute(stmt)).scalar_one_or_none()
            if admin is None:
                raise KnowledgeNotFound("同事不存在")
            grantee_name = admin.name or admin.username
        else:
            stmt = select(Role).where(Role.id == data.grantee_id)
            if self.tenant_id:
                stmt = stmt.where((Role.tenant_id == self.tenant_id) | Role.tenant_id.is_(None))
            role = (await self.db.execute(stmt)).scalar_one_or_none()
            if role is None:
                raise KnowledgeNotFound("角色不存在")
            grantee_name = role.name

        existing = (
            await self.db.execute(
                select(KnowledgeShare).where(
                    KnowledgeShare.kb_id == kb.id,
                    KnowledgeShare.grantee_type == data.grantee_type.value,
                    KnowledgeShare.grantee_id == data.grantee_id,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.permission = data.permission.value
            existing.updated_by = self.admin_id
            await self.db.commit()
            await self.db.refresh(existing)
            return existing, grantee_name

        share = KnowledgeShare(
            id=str(uuid.uuid4()),
            tenant_id=self.tenant_id,
            kb_id=kb.id,
            grantee_type=data.grantee_type.value,
            grantee_id=data.grantee_id,
            permission=data.permission.value,
            granted_by=self.admin_id,
            created_by=self.admin_id,
        )
        self.db.add(share)
        await self.db.commit()
        await self.db.refresh(share)
        return share, grantee_name

    async def remove_share(self, share_id: str) -> None:
        stmt = self._scoped(select(KnowledgeShare).where(KnowledgeShare.id == share_id), KnowledgeShare)
        share = (await self.db.execute(stmt)).scalar_one_or_none()
        if share is None:
            raise KnowledgeNotFound("共享记录不存在")
        await self.get_base(share.kb_id, "owner")
        await self.db.delete(share)
        await self.db.commit()
