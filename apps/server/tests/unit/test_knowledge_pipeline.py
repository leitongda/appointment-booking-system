"""文档处理管线：状态机 / 扫描件失败 / 可重试错误 / 维度不匹配 / 幂等重跑

SQLite 可跑（向量列以文本落库），embedding 用假提供方，不出网。
"""
import io
import uuid
from pathlib import Path

import pytest
from pypdf import PdfWriter
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import app.modules.knowledge.pipeline as pipeline_module
from app.core.config import settings
from app.enums.knowledge import KnowledgeDocStatus, KnowledgeFailedStage
from app.infrastructure.document_parser import file_extension
from app.infrastructure.document_parser.pdf import SCANNED_PDF_MESSAGE
from app.infrastructure.embedding import EmbeddingError, EmbeddingRetryableError, get_embedding_config
from app.models.knowledge import KnowledgeBase, KnowledgeChunk, KnowledgeDocument
from app.modules.knowledge.pipeline import run_document_pipeline
from tests.fixtures.knowledge import KnowledgeEnv

DIMS = 1024
TXT = "第一条 本制度适用于全院各科室。\n\n第二条 手术前 8 小时禁食固体食物，2 小时禁饮清液。".encode()


class FakeProvider:
    def __init__(self, dims: int = DIMS, model: str | None = None, error: Exception | None = None):
        self.dims = dims
        self.model_name = model or get_embedding_config().model
        self.error = error
        self.calls = 0

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return [[float(i % 7) / 7 for i in range(self.dims)] for _ in texts]


def use_provider(monkeypatch, provider: FakeProvider) -> None:
    monkeypatch.setattr(pipeline_module, "get_embedding_provider", lambda: provider)


async def seed_doc(
    db: AsyncSession, env: KnowledgeEnv, file_name: str, data: bytes | None
) -> tuple[KnowledgeBase, KnowledgeDocument]:
    kb = KnowledgeBase(
        id=str(uuid.uuid4()),
        tenant_id=env.tenant.id,
        name="管线测试库",
        owner_admin_id=env.owner.id,
        visibility="private",
        embedding_model=get_embedding_config().model,
        embedding_dims=DIMS,
    )
    key = f"tenants/{env.tenant.id}/knowledge/{kb.id}/doc/{uuid.uuid4().hex}.{file_extension(file_name)}"
    if data is not None:
        path = Path(settings.LOCAL_UPLOAD_DIR) / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    doc = KnowledgeDocument(
        id=str(uuid.uuid4()),
        tenant_id=env.tenant.id,
        kb_id=kb.id,
        title=file_name,
        file_name=file_name,
        file_key=key,
        mime_type="application/octet-stream",
        size_bytes=len(data or b""),
        status=KnowledgeDocStatus.PENDING.value,
        uploaded_by=env.owner.id,
    )
    db.add_all([kb, doc])
    await db.commit()
    return kb, doc


async def chunk_rows(db: AsyncSession, doc_id: str) -> int:
    return (await db.execute(select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.doc_id == doc_id))).scalar_one()


async def test_txt_pipeline_reaches_ready_and_updates_counts(db_session, kb_env: KnowledgeEnv, monkeypatch):
    provider = FakeProvider()
    use_provider(monkeypatch, provider)
    kb, doc = await seed_doc(db_session, kb_env, "制度.txt", TXT)

    await run_document_pipeline(db_session, doc.id)
    await db_session.refresh(doc)
    await db_session.refresh(kb)

    assert doc.status == KnowledgeDocStatus.READY.value
    assert doc.failed_stage is None and doc.error_message is None
    assert doc.processed_at is not None
    assert doc.chunk_count >= 1
    assert await chunk_rows(db_session, doc.id) == doc.chunk_count
    assert kb.doc_count == 1 and kb.chunk_count == doc.chunk_count
    assert provider.calls == 1

    seqs = (
        await db_session.execute(
            select(KnowledgeChunk.seq).where(KnowledgeChunk.doc_id == doc.id).order_by(KnowledgeChunk.seq)
        )
    ).scalars().all()
    assert seqs == list(range(doc.chunk_count))


async def test_scanned_pdf_fails_in_parsing_with_readable_reason(db_session, kb_env: KnowledgeEnv, monkeypatch):
    provider = FakeProvider()
    use_provider(monkeypatch, provider)
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    _, doc = await seed_doc(db_session, kb_env, "扫描件.pdf", buffer.getvalue())

    await run_document_pipeline(db_session, doc.id)
    await db_session.refresh(doc)

    assert doc.status == KnowledgeDocStatus.FAILED.value
    assert doc.failed_stage == KnowledgeFailedStage.PARSING.value
    assert doc.error_message == SCANNED_PDF_MESSAGE
    assert await chunk_rows(db_session, doc.id) == 0
    assert provider.calls == 0


async def test_retryable_embedding_error_propagates_and_keeps_embedding_status(
    db_session, kb_env: KnowledgeEnv, monkeypatch
):
    use_provider(monkeypatch, FakeProvider(error=EmbeddingRetryableError("HTTP 429")))
    _, doc = await seed_doc(db_session, kb_env, "制度.txt", TXT)

    with pytest.raises(EmbeddingRetryableError):
        await run_document_pipeline(db_session, doc.id)
    await db_session.refresh(doc)

    assert doc.status == KnowledgeDocStatus.EMBEDDING.value
    assert doc.failed_stage is None


async def test_dimension_mismatch_fails_in_embedding_stage(db_session, kb_env: KnowledgeEnv, monkeypatch):
    use_provider(monkeypatch, FakeProvider(dims=2048))
    _, doc = await seed_doc(db_session, kb_env, "制度.txt", TXT)

    await run_document_pipeline(db_session, doc.id)
    await db_session.refresh(doc)

    assert doc.status == KnowledgeDocStatus.FAILED.value
    assert doc.failed_stage == KnowledgeFailedStage.EMBEDDING.value
    assert "不匹配" in doc.error_message
    assert await chunk_rows(db_session, doc.id) == 0


async def test_non_retryable_embedding_error_fails(db_session, kb_env: KnowledgeEnv, monkeypatch):
    use_provider(monkeypatch, FakeProvider(error=EmbeddingError("未配置 ZHIPU_API_KEY，无法进行向量化")))
    _, doc = await seed_doc(db_session, kb_env, "制度.txt", TXT)

    await run_document_pipeline(db_session, doc.id)
    await db_session.refresh(doc)

    assert doc.status == KnowledgeDocStatus.FAILED.value
    assert doc.failed_stage == KnowledgeFailedStage.EMBEDDING.value
    assert "ZHIPU_API_KEY" in doc.error_message


async def test_rerun_is_idempotent_without_duplicate_chunks(db_session, kb_env: KnowledgeEnv, monkeypatch):
    use_provider(monkeypatch, FakeProvider())
    kb, doc = await seed_doc(db_session, kb_env, "制度.txt", TXT)

    await run_document_pipeline(db_session, doc.id)
    await db_session.refresh(doc)
    first_count = doc.chunk_count

    doc.status = KnowledgeDocStatus.PENDING.value
    await db_session.commit()
    await run_document_pipeline(db_session, doc.id)
    await db_session.refresh(doc)
    await db_session.refresh(kb)

    assert doc.status == KnowledgeDocStatus.READY.value
    assert doc.chunk_count == first_count
    assert await chunk_rows(db_session, doc.id) == first_count
    assert kb.chunk_count == first_count


async def test_missing_source_file_fails_in_parsing(db_session, kb_env: KnowledgeEnv, monkeypatch):
    use_provider(monkeypatch, FakeProvider())
    _, doc = await seed_doc(db_session, kb_env, "丢失.txt", None)

    await run_document_pipeline(db_session, doc.id)
    await db_session.refresh(doc)

    assert doc.status == KnowledgeDocStatus.FAILED.value
    assert doc.failed_stage == KnowledgeFailedStage.PARSING.value
    assert "原件不存在" in doc.error_message
