"""语义检索集成测试（仅 PostgreSQL + pgvector）：相似度排序、引用字段、processing 文档不命中"""
import os
import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.modules.knowledge.service_search as search_module
from app.core.config import settings
from app.enums.knowledge import KnowledgeDocStatus
from app.models.knowledge import KnowledgeBase, KnowledgeChunk, KnowledgeDocument
from tests.fixtures.knowledge import KnowledgeEnv

pytestmark = pytest.mark.skipif(
    os.environ.get("TEST_DATABASE_URL", "sqlite").startswith("sqlite"),
    reason="向量检索依赖 PostgreSQL + pgvector",
)

DIMS = 1024


def one_hot(index: int) -> list[float]:
    vector = [0.0] * DIMS
    vector[index] = 1.0
    return vector


class QueryProvider:
    model_name = settings.KB_EMBEDDING_MODEL
    dims = DIMS

    def __init__(self, vector: list[float]):
        self.vector = vector

    async def embed(self, texts):
        return [self.vector for _ in texts]


async def seed(db: AsyncSession, env: KnowledgeEnv):
    kb = KnowledgeBase(
        id=str(uuid.uuid4()),
        tenant_id=env.tenant.id,
        name="检索库",
        owner_admin_id=env.owner.id,
        visibility="private",
        embedding_model=settings.KB_EMBEDDING_MODEL,
        embedding_dims=DIMS,
    )
    ready = KnowledgeDocument(
        id=str(uuid.uuid4()), tenant_id=env.tenant.id, kb_id=kb.id, title="术前准备规范", file_name="a.pdf",
        file_key="k/a.pdf", mime_type="application/pdf", size_bytes=1, status=KnowledgeDocStatus.READY.value,
        processed_at=datetime.utcnow(),
    )
    processing = KnowledgeDocument(
        id=str(uuid.uuid4()), tenant_id=env.tenant.id, kb_id=kb.id, title="处理中文档", file_name="b.pdf",
        file_key="k/b.pdf", mime_type="application/pdf", size_bytes=1, status=KnowledgeDocStatus.EMBEDDING.value,
    )
    def chunk(doc_id: str, seq: int, content: str, page_no: int, section: str | None, vector: list[float]):
        return KnowledgeChunk(
            id=str(uuid.uuid4()), tenant_id=env.tenant.id, kb_id=kb.id, doc_id=doc_id, seq=seq,
            content=content, page_no=page_no, section=section, token_count=10, embedding=vector,
        )

    chunks = [
        chunk(ready.id, 0, "术前 8 小时禁食固体食物", 7, "第三章", one_hot(0)),
        chunk(ready.id, 1, "术后 6 小时可进流食", 9, "第四章", one_hot(1)),
        chunk(processing.id, 0, "处理中文档的切片，不应被命中", 1, None, one_hot(0)),
    ]
    db.add(kb)
    await db.flush()
    db.add_all([ready, processing])
    await db.flush()
    db.add_all(chunks)
    await db.commit()
    return kb, ready, chunks


async def test_search_ranks_by_cosine_and_returns_citations(
    async_client: AsyncClient, db_session, kb_env: KnowledgeEnv, monkeypatch
):
    kb, ready, chunks = await seed(db_session, kb_env)
    monkeypatch.setattr(search_module, "get_embedding_provider", lambda: QueryProvider(one_hot(0)))

    response = await async_client.post(
        "/api/v1/knowledge/search",
        json={"query": "术前禁食时间", "kbIds": [kb.id], "topK": 5},
        headers=kb_env.h(kb_env.owner),
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["total"] == 2  # processing 文档的切片不命中
    top = body["hits"][0]
    assert top["chunkId"] == chunks[0].id
    assert top["docId"] == ready.id
    assert top["docTitle"] == "术前准备规范"
    assert top["pageNo"] == 7 and top["section"] == "第三章"
    assert top["snippet"] == "术前 8 小时禁食固体食物"
    assert top["score"] > 0.99
    assert top["previewUrl"].endswith(f"/knowledge/documents/{ready.id}/file#page=7")
    assert body["hits"][1]["chunkId"] == chunks[1].id
    assert body["hits"][1]["score"] < top["score"]


async def test_search_only_returns_visible_bases_by_default(
    async_client: AsyncClient, db_session, kb_env: KnowledgeEnv, monkeypatch
):
    await seed(db_session, kb_env)
    monkeypatch.setattr(search_module, "get_embedding_provider", lambda: QueryProvider(one_hot(0)))

    response = await async_client.post(
        "/api/v1/knowledge/search", json={"query": "术前禁食时间"}, headers=kb_env.h(kb_env.colleague)
    )
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 0
