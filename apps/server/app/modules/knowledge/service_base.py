"""知识库服务公共底座：租户作用域、知识库/目录加载 + 级别校验、与管线共用的辅助函数"""
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.document_parser import SUPPORTED_EXTENSIONS, file_extension
from app.middleware.tenant_context import get_current_tenant_id
from app.models.knowledge import KnowledgeBase, KnowledgeChunk, KnowledgeDocument, KnowledgeFolder
from app.modules.knowledge.exceptions import KnowledgeInvalidFile, KnowledgeNotFound
from app.modules.knowledge.service_access import KnowledgeAccessService


def enqueue_process_document(doc_id: str) -> None:
    """投递处理任务到 knowledge 队列（独立函数，测试可替换）"""
    from app.tasks.knowledge_task import process_document

    process_document.delay(doc_id)


async def refresh_kb_counts(db: AsyncSession, kb_id: str) -> None:
    """重算知识库的文档数 / 切片数（上传、删除、处理完成后调用；不提交）"""
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None:
        return
    kb.doc_count = (
        await db.execute(select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.kb_id == kb_id))
    ).scalar_one()
    kb.chunk_count = (
        await db.execute(select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.kb_id == kb_id))
    ).scalar_one()


def validate_upload_file(filename: str, size_bytes: int) -> tuple[str, str]:
    """类型白名单 + 大小上限；返回 (扩展名, 规范 MIME)。不进入队列即拒绝。"""
    ext = file_extension(filename)
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(f".{item}" for item in SUPPORTED_EXTENSIONS)
        raise KnowledgeInvalidFile(f"不支持的文件类型 .{ext or '?'}，仅支持 {supported}")
    if size_bytes <= 0:
        raise KnowledgeInvalidFile("文件为空")
    if size_bytes > settings.KB_MAX_FILE_MB * 1024 * 1024:
        raise KnowledgeInvalidFile(f"文件超过 {settings.KB_MAX_FILE_MB}MB 上限")
    return ext, SUPPORTED_EXTENSIONS[ext]


def resolve_local_file(key: str) -> Path | None:
    """本地存储：把 key 解析为上传目录内的真实路径，防路径穿越；不存在返回 None"""
    upload_dir = Path(settings.LOCAL_UPLOAD_DIR).resolve()
    file_path = (upload_dir / key).resolve()
    if not str(file_path).startswith(str(upload_dir)):
        return None
    return file_path if file_path.is_file() else None


class KnowledgeServiceBase:
    def __init__(self, db: AsyncSession, admin: dict, tenant_id: str | None = None):
        self.db = db
        self.admin = admin
        self.admin_id: str | None = admin.get("id")
        self.tenant_id = tenant_id if tenant_id is not None else get_current_tenant_id()
        self.access = KnowledgeAccessService(db, admin, self.tenant_id)

    def _scoped(self, stmt, model):
        if self.tenant_id:
            stmt = stmt.where(model.tenant_id == self.tenant_id)
        return stmt

    async def _load_base(self, kb_id: str) -> KnowledgeBase | None:
        stmt = self._scoped(select(KnowledgeBase).where(KnowledgeBase.id == kb_id), KnowledgeBase)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_base(self, kb_id: str, level: str = "read") -> tuple[KnowledgeBase, str]:
        """加载知识库并校验级别（read/edit/owner）；返回 (kb, 实际级别)"""
        kb = await self._load_base(kb_id)
        permission = await self.access.require(kb, level)
        return kb, permission

    async def _load_folder(self, folder_id: str) -> KnowledgeFolder:
        stmt = self._scoped(select(KnowledgeFolder).where(KnowledgeFolder.id == folder_id), KnowledgeFolder)
        folder = (await self.db.execute(stmt)).scalar_one_or_none()
        if folder is None:
            raise KnowledgeNotFound("目录不存在")
        return folder

    async def _load_folder_in_kb(self, folder_id: str, kb_id: str) -> KnowledgeFolder:
        folder = await self._load_folder(folder_id)
        if folder.kb_id != kb_id:
            raise KnowledgeNotFound("目录不存在")
        return folder
