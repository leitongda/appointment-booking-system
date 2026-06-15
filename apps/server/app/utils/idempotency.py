"""幂等性工具模块

提供基于 Redis 的幂等性键支持，防止重复请求导致的副作用。
用于需要幂等保证的创建类端点（如加号申请、自定义排班创建）。
"""

import json
import logging
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

IDEMPOTENCY_PREFIX = "idempotency:"
DEFAULT_TTL = 86400  # 24 小时


async def check_idempotency(
    redis: aioredis.Redis,
    key: str,
    tenant_id: str,
) -> dict | None:
    """检查幂等性键是否已存在。

    Args:
        redis: 异步 Redis 客户端
        key: 幂等性键值（来自请求头 Idempotency-Key）
        tenant_id: 租户 ID，用于隔离不同租户的幂等性键

    Returns:
        如果键已存在，返回缓存的响应字典（包含 status_code 和 body）；
        如果键不存在，返回 None。
    """
    redis_key = f"{IDEMPOTENCY_PREFIX}{tenant_id}:{key}"
    try:
        raw = await redis.get(redis_key)
        if raw is None:
            return None
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"幂等性缓存反序列化失败: key={redis_key}, error={e}")
        return None
    except Exception as e:
        logger.error(f"幂等性检查 Redis GET 失败: key={redis_key}, error={e}")
        return None


async def store_idempotency(
    redis: aioredis.Redis,
    key: str,
    tenant_id: str,
    response_body: Any,
    ttl: int = DEFAULT_TTL,
) -> bool:
    """存储幂等性键和对应的响应。

    Args:
        redis: 异步 Redis 客户端
        key: 幂等性键值
        tenant_id: 租户 ID
        response_body: 响应体（将被 JSON 序列化存储）
        ttl: 过期时间（秒），默认 24 小时

    Returns:
        是否存储成功
    """
    redis_key = f"{IDEMPOTENCY_PREFIX}{tenant_id}:{key}"
    try:
        payload = json.dumps(response_body, ensure_ascii=False, default=str)
        await redis.setex(redis_key, ttl, payload)
        return True
    except Exception as e:
        logger.error(f"幂等性存储 Redis SET 失败: key={redis_key}, error={e}")
        return False
