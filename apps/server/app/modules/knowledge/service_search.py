"""语义检索：范围 = 调用者可见库集合（SQL 层过滤），结果携带可定位的引用来源

日志只记录 tenant / admin / kb_count / top_k / 耗时 / 命中数，不记录查询原文。
"""
import time

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.enums.knowledge import KnowledgeDocStatus
from app.infrastructure.embedding import EmbeddingError, get_embedding_provider
from app.middleware.tenant_context import get_current_tenant_id
from app.models.knowledge import KnowledgeBase, KnowledgeChunk, KnowledgeDocument
from app.modules.knowledge.exceptions import (
    KnowledgeEmbeddingMismatch,
    KnowledgeEmbeddingUnavailable,
    KnowledgeError,
    KnowledgeForbidden,
)
from app.modules.knowledge.schemas import KnowledgeSearchHit, KnowledgeSearchResponse
from app.modules.knowledge.service_access import KnowledgeAccessService

HNSW_EF_SEARCH = 100


def build_preview_url(doc_id: str, page_no: int | None) -> str:
    """相对 API 路径（不含 baseURL），前端据此以带鉴权的方式打开预览并定位页码"""
    url = f"{settings.API_V1_STR}/knowledge/documents/{doc_id}/file"
    return f"{url}#page={page_no}" if page_no else url


class KnowledgeSearchService:
    def __init__(self, db: AsyncSession, admin: dict, tenant_id: str | None = None):
        self.db = db
        self.admin = admin
        self.tenant_id = tenant_id if tenant_id is not None else get_current_tenant_id()
        self.access = KnowledgeAccessService(db, admin, self.tenant_id)

    async def _resolve_target_kb_ids(self, kb_ids: list[str] | None) -> list[str]:
        visible = await self.access.visible_kb_ids()
        if visible is None:
            stmt = select(KnowledgeBase.id)
            if self.tenant_id:
                stmt = stmt.where(KnowledgeBase.tenant_id == self.tenant_id)
            visible = set((await self.db.execute(stmt)).scalars().all())

        if kb_ids:
            requested = {kb_id for kb_id in kb_ids if kb_id}
            if requested - visible:
                raise KnowledgeForbidden("包含无权访问的知识库")
            return sorted(requested)
        return sorted(visible)

    async def _assert_embedding_consistent(self, kb_ids: list[str]) -> None:
        stmt = select(KnowledgeBase.embedding_model, KnowledgeBase.embedding_dims).where(KnowledgeBase.id.in_(kb_ids))
        for model, dims in (await self.db.execute(stmt)).all():
            if model != settings.KB_EMBEDDING_MODEL or dims != settings.KB_EMBEDDING_DIMS:
                raise KnowledgeEmbeddingMismatch("该知识库的向量模型与当前配置不一致，需重建索引后方可检索")

    async def search(self, query: str, kb_ids: list[str] | None, top_k: int) -> KnowledgeSearchResponse:
        started = time.perf_counter()
        if top_k > settings.KB_SEARCH_TOP_K_MAX:
            raise KnowledgeError(f"top_k 不能超过 {settings.KB_SEARCH_TOP_K_MAX}", error_code="KB_TOP_K_EXCEEDED")

        target_ids = await self._resolve_target_kb_ids(kb_ids)
        if not target_ids:
            return KnowledgeSearchResponse(hits=[], total=0, took_ms=0)
        await self._assert_embedding_consistent(target_ids)

        try:
            provider = get_embedding_provider()
            query_vector = (await provider.embed([query]))[0]
        except EmbeddingError as exc:
            logger.warning(f"[knowledge] 查询向量化失败: {type(exc).__name__}")
            raise KnowledgeEmbeddingUnavailable("检索服务暂不可用，请稍后重试") from exc
        if len(query_vector) != settings.KB_EMBEDDING_DIMS:
            raise KnowledgeEmbeddingUnavailable("检索服务返回的向量维度异常")

        if self.db.bind is not None and self.db.bind.dialect.name == "postgresql":
            await self.db.execute(text(f"SET LOCAL hnsw.ef_search = {int(HNSW_EF_SEARCH)}"))

        distance = KnowledgeChunk.embedding.cosine_distance(query_vector)
        stmt = (
            select(KnowledgeChunk, KnowledgeDocument.title, distance.label("distance"))
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.doc_id)
            .where(
                KnowledgeChunk.kb_id.in_(target_ids),
                KnowledgeDocument.status == KnowledgeDocStatus.READY.value,
            )
            .order_by(distance)
            .limit(top_k)
        )
        rows = (await self.db.execute(stmt)).all()

        hits = [
            KnowledgeSearchHit(
                chunk_id=chunk.id,
                doc_id=chunk.doc_id,
                doc_title=title,
                kb_id=chunk.kb_id,
                page_no=chunk.page_no,
                section=chunk.section,
                snippet=chunk.content,
                score=round(max(0.0, 1.0 - float(dist)), 6),
                preview_url=build_preview_url(chunk.doc_id, chunk.page_no),
            )
            for chunk, title, dist in rows
        ]
        took_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            f"[knowledge] search tenant={self.tenant_id} admin={self.admin.get('id')} "
            f"kb_count={len(target_ids)} top_k={top_k} hits={len(hits)} took_ms={took_ms}"
        )
        return KnowledgeSearchResponse(hits=hits, total=len(hits), took_ms=took_ms)
