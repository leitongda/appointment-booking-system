"""embedding 提供方：OpenAI 兼容客户端（MockTransport，不出网）+ 预设/环境变量解析"""
import json

import httpx
import pytest

import app.infrastructure.embedding as embedding_module
from app.core.config import settings
from app.infrastructure.embedding import (
    EmbeddingError,
    EmbeddingRetryableError,
    get_embedding_config,
    get_embedding_provider,
)
from app.infrastructure.embedding.openai_compatible import OpenAICompatibleEmbeddingProvider

DIMS = 4


def make_provider(handler, *, batch_size: int = 32, send_dimensions: bool = True) -> OpenAICompatibleEmbeddingProvider:
    return OpenAICompatibleEmbeddingProvider(
        api_key="test-key",
        model="test-model",
        dims=DIMS,
        base_url="https://embed.example.com/v1/",
        batch_size=batch_size,
        send_dimensions=send_dimensions,
        transport=httpx.MockTransport(handler),
    )


def ok_response(count: int, reverse: bool = False) -> httpx.Response:
    items = [{"index": i, "embedding": [float(i)] * DIMS} for i in range(count)]
    if reverse:
        items.reverse()
    return httpx.Response(200, json={"data": items, "usage": {"total_tokens": count * 3}})


# ==================== 客户端 ====================

async def test_embed_sends_bearer_dimensions_and_restores_index_order():
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return ok_response(3, reverse=True)

    vectors = await make_provider(handler).embed(["甲", "乙", "丙"])

    assert vectors == [[0.0] * DIMS, [1.0] * DIMS, [2.0] * DIMS]
    request = captured[0]
    assert request.url == "https://embed.example.com/v1/embeddings"
    assert request.headers["Authorization"] == "Bearer test-key"
    payload = json.loads(request.content)
    assert payload == {"model": "test-model", "input": ["甲", "乙", "丙"], "dimensions": DIMS}


async def test_embed_omits_dimensions_when_disabled_and_splits_batches():
    payloads: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        payloads.append(payload)
        return ok_response(len(payload["input"]))

    vectors = await make_provider(handler, batch_size=2, send_dimensions=False).embed(["a", "b", "c", "d", "e"])

    assert len(vectors) == 5
    assert [len(p["input"]) for p in payloads] == [2, 2, 1]
    assert all("dimensions" not in p for p in payloads)


async def test_embed_empty_input_makes_no_request():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("不应发起请求")

    assert await make_provider(handler).embed([]) == []


@pytest.mark.parametrize("status", [429, 500, 503])
async def test_rate_limit_and_server_errors_are_retryable(status: int):
    provider = make_provider(lambda request: httpx.Response(status, json={"error": "busy"}))
    with pytest.raises(EmbeddingRetryableError):
        await provider.embed(["x"])


async def test_client_errors_are_not_retryable_and_hide_upstream_body():
    provider = make_provider(lambda request: httpx.Response(401, json={"error": {"message": "secret upstream detail"}}))
    with pytest.raises(EmbeddingError) as excinfo:
        await provider.embed(["x"])
    assert not isinstance(excinfo.value, EmbeddingRetryableError)
    assert "secret upstream detail" not in str(excinfo.value)


async def test_network_error_is_retryable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout", request=request)

    with pytest.raises(EmbeddingRetryableError):
        await make_provider(handler).embed(["x"])


async def test_count_mismatch_and_malformed_body_fail_fast():
    with pytest.raises(EmbeddingError):
        await make_provider(lambda request: ok_response(1)).embed(["a", "b"])
    with pytest.raises(EmbeddingError):
        await make_provider(lambda request: httpx.Response(200, json={"unexpected": True})).embed(["a"])


# ==================== 配置解析 ====================

def test_zhipu_preset_falls_back_to_legacy_env(monkeypatch):
    monkeypatch.setattr(settings, "KB_EMBEDDING_PROVIDER", "zhipu")
    monkeypatch.setattr(settings, "KB_EMBEDDING_BASE_URL", None)
    monkeypatch.setattr(settings, "KB_EMBEDDING_API_KEY", None)
    monkeypatch.setattr(settings, "KB_EMBEDDING_MODEL", None)
    monkeypatch.setattr(settings, "KB_EMBEDDING_SEND_DIMENSIONS", "")
    monkeypatch.setattr(settings, "ZHIPU_API_KEY", "legacy-key")

    config = get_embedding_config()
    assert config.provider == "zhipu"
    assert config.model == "embedding-3"
    assert config.base_url == settings.ZHIPU_BASE_URL
    assert config.api_key == "legacy-key"
    assert config.send_dimensions is True
    assert config.dims == settings.KB_EMBEDDING_DIMS


def test_siliconflow_preset_uses_free_bge_m3_without_dimensions_param(monkeypatch):
    monkeypatch.setattr(settings, "KB_EMBEDDING_PROVIDER", "siliconflow")
    monkeypatch.setattr(settings, "KB_EMBEDDING_BASE_URL", None)
    monkeypatch.setattr(settings, "KB_EMBEDDING_API_KEY", "sf-key")
    monkeypatch.setattr(settings, "KB_EMBEDDING_MODEL", None)
    monkeypatch.setattr(settings, "KB_EMBEDDING_SEND_DIMENSIONS", "")

    config = get_embedding_config()
    assert config.base_url == "https://api.siliconflow.cn/v1"
    assert config.model == "BAAI/bge-m3"
    assert config.send_dimensions is False

    provider = get_embedding_provider()
    assert isinstance(provider, OpenAICompatibleEmbeddingProvider)
    assert provider.model_name == "BAAI/bge-m3" and provider.send_dimensions is False


def test_explicit_env_overrides_preset(monkeypatch):
    monkeypatch.setattr(settings, "KB_EMBEDDING_PROVIDER", "siliconflow")
    monkeypatch.setattr(settings, "KB_EMBEDDING_BASE_URL", "https://proxy.internal/v1")
    monkeypatch.setattr(settings, "KB_EMBEDDING_API_KEY", "k")
    monkeypatch.setattr(settings, "KB_EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5")
    monkeypatch.setattr(settings, "KB_EMBEDDING_SEND_DIMENSIONS", "true")

    config = get_embedding_config()
    assert config.base_url == "https://proxy.internal/v1"
    assert config.model == "BAAI/bge-large-zh-v1.5"
    assert config.send_dimensions is True


def test_openai_compatible_requires_base_url_and_model(monkeypatch):
    monkeypatch.setattr(settings, "KB_EMBEDDING_PROVIDER", "openai_compatible")
    monkeypatch.setattr(settings, "KB_EMBEDDING_BASE_URL", None)
    monkeypatch.setattr(settings, "KB_EMBEDDING_MODEL", None)
    with pytest.raises(EmbeddingError, match="KB_EMBEDDING_BASE_URL"):
        get_embedding_config()

    monkeypatch.setattr(settings, "KB_EMBEDDING_BASE_URL", "https://gw.example.com/v1")
    with pytest.raises(EmbeddingError, match="KB_EMBEDDING_MODEL"):
        get_embedding_config()


def test_unknown_provider_and_missing_key_raise_non_retryable(monkeypatch):
    monkeypatch.setattr(settings, "KB_EMBEDDING_PROVIDER", "sensenova")
    with pytest.raises(EmbeddingError, match="不支持的 embedding 提供方"):
        get_embedding_config()

    monkeypatch.setattr(settings, "KB_EMBEDDING_PROVIDER", "siliconflow")
    monkeypatch.setattr(settings, "KB_EMBEDDING_API_KEY", None)
    monkeypatch.setattr(settings, "KB_EMBEDDING_MODEL", None)
    monkeypatch.setattr(settings, "KB_EMBEDDING_BASE_URL", None)
    with pytest.raises(EmbeddingError, match="KB_EMBEDDING_API_KEY") as excinfo:
        get_embedding_provider()
    assert not isinstance(excinfo.value, EmbeddingRetryableError)
    assert set(embedding_module.PRESETS) == {"zhipu", "siliconflow", "dashscope", "openai_compatible"}
