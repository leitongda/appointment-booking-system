"""文档处理管线：解析 → 切片 → 向量化 → 写切片；状态机全程落库，幂等可重试

与 Celery 解耦：run_document_pipeline 只依赖 AsyncSession，便于测试直接调用。
EmbeddingRetryableError 原样抛出交给任务层退避重试（此时状态停留在 embedding）。
"""
import asyncio
import uuid
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.enums.knowledge import KnowledgeDocStatus, KnowledgeFailedStage
from app.infrastructure.document_parser import ParseError, file_extension, get_parser
from app.infrastructure.embedding import (
    EmbeddingError,
    EmbeddingRetryableError,
    get_embedding_provider,
)
from app.infrastructure.storage import get_storage
from app.models.knowledge import KnowledgeBase, KnowledgeChunk, KnowledgeDocument
from app.modules.knowledge.chunker import chunk_blocks
from app.modules.knowledge.service_base import refresh_kb_counts, resolve_local_file


async def _set_status(db: AsyncSession, doc: KnowledgeDocument, status: KnowledgeDocStatus) -> None:
    doc.status = status.value
    await db.commit()


async def _fail(db: AsyncSession, doc: KnowledgeDocument, stage: KnowledgeFailedStage, message: str) -> None:
    doc.status = KnowledgeDocStatus.FAILED.value
    doc.failed_stage = stage.value
    doc.error_message = (message or "处理失败")[:2000]
    doc.processed_at = datetime.utcnow()
    await db.commit()
    logger.warning(f"[knowledge] 文档处理失败 doc={doc.id} stage={stage.value}")


async def mark_document_failed(db: AsyncSession, doc_id: str, stage: KnowledgeFailedStage, message: str) -> None:
    """任务层重试耗尽后调用"""
    doc = await db.get(KnowledgeDocument, doc_id)
    if doc is not None:
        await _fail(db, doc, stage, message)


async def _materialize(file_key: str, ext: str) -> tuple[Path, bool]:
    """拿到可读的本地文件路径；返回 (路径, 是否为需清理的临时文件)

    local 存储直接读上传目录（零临时文件）；其他存储下载到 KB_TMP_DIR（磁盘卷，非 tmpfs）。
    """
    if settings.STORAGE_TYPE.lower() == "local":
        path = resolve_local_file(file_key)
        if path is None:
            raise ParseError("原件不存在或已被移除")
        return path, False

    tmp_dir = Path(settings.KB_TMP_DIR)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    target = tmp_dir / f"{uuid.uuid4().hex}.{ext}"
    url = await get_storage().get_url(file_key)
    try:
        async with httpx.AsyncClient(timeout=120.0) as client, client.stream("GET", url) as response:
            response.raise_for_status()
            with target.open("wb") as handle:
                async for chunk in response.aiter_bytes(1024 * 1024):
                    handle.write(chunk)
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise ParseError(f"原件下载失败（{type(exc).__name__}）") from exc
    return target, True


async def run_document_pipeline(db: AsyncSession, doc_id: str) -> None:
    doc = await db.get(KnowledgeDocument, doc_id)
    if doc is None:
        logger.warning(f"[knowledge] 文档不存在，跳过处理 doc={doc_id}")
        return
    kb = await db.get(KnowledgeBase, doc.kb_id)
    if kb is None:
        await _fail(db, doc, KnowledgeFailedStage.PARSING, "所属知识库已不存在")
        return

    # 幂等：无论上次停在哪，先清掉旧切片
    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.doc_id == doc.id))
    doc.failed_stage = None
    doc.error_message = None
    await _set_status(db, doc, KnowledgeDocStatus.PARSING)

    ext = file_extension(doc.file_name)
    path: Path | None = None
    is_temp = False
    try:
        path, is_temp = await _materialize(doc.file_key, ext)
        result = await asyncio.to_thread(get_parser(ext).parse, path)
        chunks = chunk_blocks(result.blocks, settings.KB_CHUNK_CHARS, settings.KB_CHUNK_OVERLAP)
        if not chunks:
            raise ParseError("文档未提取到任何文本")
        doc.page_count = result.page_count
    except ParseError as exc:
        await _fail(db, doc, KnowledgeFailedStage.PARSING, str(exc))
        return
    except Exception as exc:
        logger.exception(f"[knowledge] 解析异常 doc={doc.id}")
        await _fail(db, doc, KnowledgeFailedStage.PARSING, f"解析失败（{type(exc).__name__}）")
        return
    finally:
        if is_temp and path is not None:
            path.unlink(missing_ok=True)

    await _set_status(db, doc, KnowledgeDocStatus.EMBEDDING)

    try:
        provider = get_embedding_provider()
    except EmbeddingError as exc:
        await _fail(db, doc, KnowledgeFailedStage.EMBEDDING, str(exc))
        return
    if provider.model_name != kb.embedding_model or provider.dims != kb.embedding_dims:
        await _fail(
            db,
            doc,
            KnowledgeFailedStage.EMBEDDING,
            f"embedding 模型/维度不匹配（知识库 {kb.embedding_model}/{kb.embedding_dims}，"
            f"当前配置 {provider.model_name}/{provider.dims}），需重建知识库",
        )
        return

    try:
        vectors = await provider.embed([chunk.content for chunk in chunks])
    except EmbeddingRetryableError:
        raise
    except EmbeddingError as exc:
        await _fail(db, doc, KnowledgeFailedStage.EMBEDDING, str(exc))
        return

    if len(vectors) != len(chunks) or any(len(vector) != kb.embedding_dims for vector in vectors):
        await _fail(db, doc, KnowledgeFailedStage.EMBEDDING, "向量维度与知识库不匹配，拒绝写入")
        return

    db.add_all(
        KnowledgeChunk(
            id=str(uuid.uuid4()),
            tenant_id=doc.tenant_id,
            kb_id=kb.id,
            doc_id=doc.id,
            seq=chunk.seq,
            content=chunk.content,
            page_no=chunk.page_no,
            section=chunk.section,
            token_count=chunk.token_count,
            embedding=vector,
        )
        for chunk, vector in zip(chunks, vectors, strict=True)
    )
    doc.status = KnowledgeDocStatus.READY.value
    doc.failed_stage = None
    doc.error_message = None
    doc.chunk_count = len(chunks)
    doc.processed_at = datetime.utcnow()
    await db.flush()
    await refresh_kb_counts(db, kb.id)
    await db.commit()
    logger.info(f"[knowledge] 文档处理完成 doc={doc.id} chunks={len(chunks)} pages={doc.page_count}")
