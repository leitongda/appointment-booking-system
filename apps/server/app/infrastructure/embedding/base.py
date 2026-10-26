"""Embedding 提供方抽象

生产机（3.6G 内存）无法自托管模型，首个实现走国内厂商 API（智谱 embedding-3）。
替换提供方：实现 BaseEmbeddingProvider 并在 get_embedding_provider 中按 KB_EMBEDDING_PROVIDER 装配。
"""
from abc import ABC, abstractmethod


class EmbeddingError(Exception):
    """不可重试的 embedding 错误（配置缺失、4xx、响应格式异常）"""


class EmbeddingRetryableError(EmbeddingError):
    """可重试错误（429 / 5xx / 网络超时），任务层按指数退避重试"""


class BaseEmbeddingProvider(ABC):
    """所有提供方必须声明 model_name / dims，用于与知识库记录的模型指纹比对"""

    model_name: str
    dims: int

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """批量向量化，返回顺序与输入一致"""
