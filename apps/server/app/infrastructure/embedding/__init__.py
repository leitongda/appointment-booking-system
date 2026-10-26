"""Embedding 提供方装配：按 KB_EMBEDDING_PROVIDER 解析预设 + 环境变量覆盖

所有预设都走 OpenAI 兼容 /embeddings 接口，默认模型均为 1024 维（与 knowledge_chunks.embedding 一致）：
- zhipu       智谱 embedding-3（¥0.5 / 百万 token）
- siliconflow 硅基流动 BAAI/bge-m3（免费；不接受 dimensions 参数）
- dashscope   阿里云百炼 text-embedding-v3
- openai_compatible 任意兼容网关，KB_EMBEDDING_BASE_URL / KB_EMBEDDING_API_KEY / KB_EMBEDDING_MODEL 必填
"""
from dataclasses import dataclass

from app.core.config import settings
from app.infrastructure.embedding.base import (
    BaseEmbeddingProvider,
    EmbeddingError,
    EmbeddingRetryableError,
)

__all__ = [
    "PRESETS",
    "BaseEmbeddingProvider",
    "EmbeddingConfig",
    "EmbeddingError",
    "EmbeddingRetryableError",
    "get_embedding_config",
    "get_embedding_provider",
]


@dataclass(frozen=True)
class EmbeddingPreset:
    base_url: str | None
    model: str | None
    send_dimensions: bool


PRESETS: dict[str, EmbeddingPreset] = {
    # base_url 为 None 时取 ZHIPU_BASE_URL
    "zhipu": EmbeddingPreset(base_url=None, model="embedding-3", send_dimensions=True),
    "siliconflow": EmbeddingPreset(
        base_url="https://api.siliconflow.cn/v1", model="BAAI/bge-m3", send_dimensions=False
    ),
    "dashscope": EmbeddingPreset(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", model="text-embedding-v3", send_dimensions=True
    ),
    "openai_compatible": EmbeddingPreset(base_url=None, model=None, send_dimensions=True),
}


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str
    base_url: str
    api_key: str | None
    model: str
    dims: int
    send_dimensions: bool
    batch_size: int


def get_embedding_config() -> EmbeddingConfig:
    """解析生效的 embedding 配置（不要求 key 存在，供建库记录模型指纹等只读场景使用）"""
    provider = (settings.KB_EMBEDDING_PROVIDER or "").lower().strip()
    preset = PRESETS.get(provider)
    if preset is None:
        raise EmbeddingError(f"不支持的 embedding 提供方: {provider or '(空)'}，可选 {', '.join(PRESETS)}")

    base_url = settings.KB_EMBEDDING_BASE_URL or preset.base_url
    if not base_url and provider == "zhipu":
        base_url = settings.ZHIPU_BASE_URL
    if not base_url:
        raise EmbeddingError(f"embedding 提供方 {provider} 需要配置 KB_EMBEDDING_BASE_URL")

    model = settings.KB_EMBEDDING_MODEL or preset.model
    if not model:
        raise EmbeddingError(f"embedding 提供方 {provider} 需要配置 KB_EMBEDDING_MODEL")

    api_key = settings.KB_EMBEDDING_API_KEY
    if not api_key and provider == "zhipu":
        api_key = settings.ZHIPU_API_KEY

    override = (settings.KB_EMBEDDING_SEND_DIMENSIONS or "").strip().lower()
    if override in ("true", "1", "yes"):
        send_dimensions = True
    elif override in ("false", "0", "no"):
        send_dimensions = False
    else:
        send_dimensions = preset.send_dimensions
    return EmbeddingConfig(
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        model=model,
        dims=settings.KB_EMBEDDING_DIMS,
        send_dimensions=send_dimensions,
        batch_size=settings.KB_EMBED_BATCH_SIZE,
    )


def get_embedding_provider() -> BaseEmbeddingProvider:
    """装配可调用的提供方；key 缺失抛 EmbeddingError（不可重试）"""
    config = get_embedding_config()
    if not config.api_key:
        hint = "ZHIPU_API_KEY 或 KB_EMBEDDING_API_KEY" if config.provider == "zhipu" else "KB_EMBEDDING_API_KEY"
        raise EmbeddingError(f"未配置 {hint}，无法进行向量化")
    from app.infrastructure.embedding.openai_compatible import OpenAICompatibleEmbeddingProvider

    return OpenAICompatibleEmbeddingProvider(
        api_key=config.api_key,
        model=config.model,
        dims=config.dims,
        base_url=config.base_url,
        batch_size=config.batch_size,
        send_dimensions=config.send_dimensions,
    )
