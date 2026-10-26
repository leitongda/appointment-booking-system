"""Embedding 提供方装配"""
from app.core.config import settings
from app.infrastructure.embedding.base import (
    BaseEmbeddingProvider,
    EmbeddingError,
    EmbeddingRetryableError,
)

__all__ = [
    "BaseEmbeddingProvider",
    "EmbeddingError",
    "EmbeddingRetryableError",
    "get_embedding_provider",
]


def get_embedding_provider() -> BaseEmbeddingProvider:
    """按 KB_EMBEDDING_PROVIDER 装配提供方；配置缺失抛 EmbeddingError（不可重试）"""
    provider = (settings.KB_EMBEDDING_PROVIDER or "").lower()
    if provider == "zhipu":
        if not settings.ZHIPU_API_KEY:
            raise EmbeddingError("未配置 ZHIPU_API_KEY，无法进行向量化")
        from app.infrastructure.embedding.zhipu import ZhipuEmbeddingProvider

        return ZhipuEmbeddingProvider(
            api_key=settings.ZHIPU_API_KEY,
            model=settings.KB_EMBEDDING_MODEL,
            dims=settings.KB_EMBEDDING_DIMS,
            base_url=settings.ZHIPU_BASE_URL,
            batch_size=settings.KB_EMBED_BATCH_SIZE,
        )
    raise EmbeddingError(f"不支持的 embedding 提供方: {provider or '(空)'}")
