"""智谱 AI embedding 提供方（embedding-3，OpenAI 兼容接口）

日志只记录调用次数 / token 数 / 错误类别，不记录任何文本内容。
"""
import httpx

from app.core.logging import logger
from app.infrastructure.embedding.base import (
    BaseEmbeddingProvider,
    EmbeddingError,
    EmbeddingRetryableError,
)


class ZhipuEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        dims: int,
        base_url: str,
        batch_size: int = 32,
        timeout: float = 30.0,
    ):
        self.api_key = api_key
        self.model_name = model
        self.dims = dims
        self.base_url = base_url.rstrip("/")
        self.batch_size = max(1, batch_size)
        self.timeout = timeout

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for start in range(0, len(texts), self.batch_size):
                batch = texts[start:start + self.batch_size]
                vectors.extend(await self._embed_batch(client, batch))
        return vectors

    async def _embed_batch(self, client: httpx.AsyncClient, batch: list[str]) -> list[list[float]]:
        try:
            response = await client.post(
                f"{self.base_url}/embeddings",
                json={"model": self.model_name, "input": batch, "dimensions": self.dims},
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        except httpx.HTTPError as exc:
            logger.warning(f"[knowledge] embedding 网络错误: {type(exc).__name__}")
            raise EmbeddingRetryableError(f"embedding 提供方网络错误: {type(exc).__name__}") from exc

        if response.status_code == 429 or response.status_code >= 500:
            logger.warning(f"[knowledge] embedding 提供方返回 HTTP {response.status_code}")
            raise EmbeddingRetryableError(f"embedding 提供方 HTTP {response.status_code}")
        if response.status_code >= 400:
            logger.error(f"[knowledge] embedding 提供方拒绝请求 HTTP {response.status_code}")
            raise EmbeddingError(f"embedding 提供方 HTTP {response.status_code}")

        try:
            payload = response.json()
            items = payload["data"]
        except (ValueError, KeyError, TypeError) as exc:
            raise EmbeddingError("embedding 提供方响应格式异常") from exc
        if len(items) != len(batch):
            raise EmbeddingError(f"embedding 返回数量不匹配: 期望 {len(batch)} 实际 {len(items)}")

        items = sorted(items, key=lambda item: item.get("index", 0))
        usage = payload.get("usage") or {}
        logger.info(
            f"[knowledge] embedding 调用成功 batch={len(batch)} tokens={usage.get('total_tokens', '-')}"
        )
        return [list(map(float, item["embedding"])) for item in items]
