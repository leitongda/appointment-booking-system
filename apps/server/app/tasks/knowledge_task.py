"""知识库文档处理任务（独立 knowledge 队列，由单并发 worker 消费）

compose: celery -A app.celery_app worker -Q knowledge -c 1 --max-tasks-per-child=20 --max-memory-per-child=400000
可重试错误（embedding 提供方 429/5xx/网络）按 60s/180s/600s 退避重试 3 次，耗尽后置 failed(embedding)。
"""
import asyncio

from celery.exceptions import MaxRetriesExceededError

from app.celery_app import celery_app
from app.core.logging import logger
from app.db.session import get_async_db_context
from app.enums.knowledge import KnowledgeFailedStage
from app.infrastructure.embedding import EmbeddingRetryableError
from app.modules.knowledge.pipeline import mark_document_failed, run_document_pipeline

RETRY_COUNTDOWNS = (60, 180, 600)
RETRY_EXHAUSTED_MESSAGE = "向量化服务持续不可用（已重试 3 次），请稍后重新处理"


@celery_app.task(
    bind=True,
    name="app.tasks.knowledge_task.process_document",
    max_retries=len(RETRY_COUNTDOWNS),
    time_limit=1800,
    soft_time_limit=1500,
)
def process_document(self, doc_id: str) -> dict:
    """解析 → 切片 → 向量化 → 写切片；状态机见 pipeline.run_document_pipeline"""

    async def _run() -> None:
        async for db in get_async_db_context():
            await run_document_pipeline(db, doc_id)
            return

    async def _mark_failed() -> None:
        async for db in get_async_db_context():
            await mark_document_failed(db, doc_id, KnowledgeFailedStage.EMBEDDING, RETRY_EXHAUSTED_MESSAGE)
            return

    try:
        asyncio.run(_run())
    except EmbeddingRetryableError as exc:
        attempt = self.request.retries
        logger.warning(f"[knowledge] 向量化可重试错误 doc={doc_id} attempt={attempt}: {type(exc).__name__}")
        try:
            raise self.retry(exc=exc, countdown=RETRY_COUNTDOWNS[min(attempt, len(RETRY_COUNTDOWNS) - 1)])
        except MaxRetriesExceededError:
            asyncio.run(_mark_failed())
            return {"doc_id": doc_id, "status": "failed"}
    return {"doc_id": doc_id, "status": "done"}
