"""幂等性工具单元测试

测试 check_idempotency / store_idempotency 的核心行为：
- 首次请求正常通过
- 重复请求返回缓存响应
- 不同租户相同 key 产生不同缓存条目
- 缺少 key 时不做幂等检查
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.utils.idempotency import (
    check_idempotency,
    store_idempotency,
    IDEMPOTENCY_PREFIX,
)


@pytest.fixture
def mock_redis_client():
    """模拟 redis.asyncio.Redis 客户端"""
    client = AsyncMock()
    # 使用内存 dict 模拟 Redis 存储
    _store = {}

    async def mock_get(key):
        return _store.get(key)

    async def mock_setex(key, ttl, value):
        _store[key] = value
        return True

    client.get = AsyncMock(side_effect=mock_get)
    client.setex = AsyncMock(side_effect=mock_setex)
    client._store = _store  # 暴露内部存储供测试断言
    return client


@pytest.mark.asyncio
async def test_check_idempotency_returns_none_when_key_not_found(mock_redis_client):
    """键不存在时返回 None"""
    result = await check_idempotency(mock_redis_client, "nonexistent-key", "tenant-1")
    assert result is None


@pytest.mark.asyncio
async def test_store_and_check_idempotency(mock_redis_client):
    """存储后能正确读取"""
    response_body = {"id": "req-1", "status": "ok"}
    stored = await store_idempotency(mock_redis_client, "key-1", "tenant-1", response_body)
    assert stored is True

    result = await check_idempotency(mock_redis_client, "key-1", "tenant-1")
    assert result == response_body


@pytest.mark.asyncio
async def test_different_tenant_same_key_produces_different_entries(mock_redis_client):
    """不同租户使用相同 key 时互不影响"""
    response_a = {"id": "a", "data": "tenant-a-response"}
    response_b = {"id": "b", "data": "tenant-b-response"}

    await store_idempotency(mock_redis_client, "same-key", "tenant-a", response_a)
    await store_idempotency(mock_redis_client, "same-key", "tenant-b", response_b)

    result_a = await check_idempotency(mock_redis_client, "same-key", "tenant-a")
    result_b = await check_idempotency(mock_redis_client, "same-key", "tenant-b")

    assert result_a == response_a
    assert result_b == response_b
    assert result_a != result_b


@pytest.mark.asyncio
async def test_check_idempotency_handles_corrupted_json(mock_redis_client):
    """缓存值为非法 JSON 时返回 None 而非抛异常"""
    redis_key = f"{IDEMPOTENCY_PREFIX}tenant-1:bad-key"
    mock_redis_client._store[redis_key] = "not-valid-json{{"

    result = await check_idempotency(mock_redis_client, "bad-key", "tenant-1")
    assert result is None


@pytest.mark.asyncio
async def test_store_idempotency_uses_correct_redis_key_format(mock_redis_client):
    """Redis key 格式为 idempotency:{tenant_id}:{key}"""
    await store_idempotency(mock_redis_client, "my-key", "t-42", {"ok": True})

    expected_key = f"{IDEMPOTENCY_PREFIX}t-42:my-key"
    assert expected_key in mock_redis_client._store
    stored_value = json.loads(mock_redis_client._store[expected_key])
    assert stored_value == {"ok": True}


@pytest.mark.asyncio
async def test_store_idempotency_with_complex_response(mock_redis_client):
    """复杂嵌套响应能正确序列化/反序列化"""
    complex_response = {
        "id": "complex-1",
        "items": [{"name": "a", "value": 1}, {"name": "b", "value": 2}],
        "nested": {"deep": {"field": "value"}},
        "number": 42,
        "flag": True,
    }
    await store_idempotency(mock_redis_client, "complex", "t-1", complex_response)
    result = await check_idempotency(mock_redis_client, "complex", "t-1")
    assert result == complex_response
