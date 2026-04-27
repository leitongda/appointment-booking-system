"""Rule engine Redis cache layer."""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.redis import RedisCache

logger = logging.getLogger(__name__)

CACHE_PREFIX = "rule"
CACHE_TTL = 3600  # 1 hour


@dataclass
class CachedRuleWindow:
    """Cached rule window representation."""
    id: str
    name: Optional[str]
    action: str
    reference_point: str
    open_offset_sec: Optional[int]
    close_offset_sec: Optional[int]
    open_inclusive: Optional[bool]
    close_inclusive: Optional[bool]
    fail_policy: str
    fail_tag: Optional[str]
    enabled: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CachedRuleWindow":
        return cls(
            id=data["id"],
            name=data.get("name"),
            action=data["action"],
            reference_point=data["reference_point"],
            open_offset_sec=data.get("open_offset_sec"),
            close_offset_sec=data.get("close_offset_sec"),
            open_inclusive=data.get("open_inclusive"),
            close_inclusive=data.get("close_inclusive"),
            fail_policy=data["fail_policy"],
            fail_tag=data.get("fail_tag"),
            enabled=data["enabled"],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "action": self.action,
            "reference_point": self.reference_point,
            "open_offset_sec": self.open_offset_sec,
            "close_offset_sec": self.close_offset_sec,
            "open_inclusive": self.open_inclusive,
            "close_inclusive": self.close_inclusive,
            "fail_policy": self.fail_policy,
            "fail_tag": self.fail_tag,
            "enabled": self.enabled,
        }


@dataclass
class CachedRuleSet:
    """Cached rule set representation compatible with RuleSet ORM interface."""
    id: str
    name: str
    enabled: bool
    priority: int
    time_source: str
    timezone_source: str
    compare_precision: str
    default_open_inclusive: bool
    default_close_inclusive: bool
    rounding_mode: str
    clock_skew_tolerance_sec: int
    tenant_id: Optional[str] = None
    store_id: Optional[str] = None
    department_id: Optional[str] = None
    description: Optional[str] = None
    windows: List[CachedRuleWindow] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CachedRuleSet":
        windows = [CachedRuleWindow.from_dict(w) for w in data.get("windows", [])]
        return cls(
            id=data["id"],
            name=data["name"],
            enabled=data["enabled"],
            priority=data["priority"],
            time_source=data.get("time_source", "SERVER"),
            timezone_source=data.get("timezone_source", "HOSPITAL"),
            compare_precision=data.get("compare_precision", "SECOND"),
            default_open_inclusive=data.get("default_open_inclusive", True),
            default_close_inclusive=data.get("default_close_inclusive", False),
            rounding_mode=data.get("rounding_mode", "NONE"),
            clock_skew_tolerance_sec=data.get("clock_skew_tolerance_sec", 5),
            tenant_id=data.get("tenant_id"),
            store_id=data.get("store_id"),
            department_id=data.get("department_id"),
            description=data.get("description"),
            windows=windows,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "priority": self.priority,
            "time_source": self.time_source,
            "timezone_source": self.timezone_source,
            "compare_precision": self.compare_precision,
            "default_open_inclusive": self.default_open_inclusive,
            "default_close_inclusive": self.default_close_inclusive,
            "rounding_mode": self.rounding_mode,
            "clock_skew_tolerance_sec": self.clock_skew_tolerance_sec,
            "tenant_id": self.tenant_id,
            "store_id": self.store_id,
            "department_id": self.department_id,
            "description": self.description,
            "windows": [w.to_dict() for w in self.windows],
        }


class RuleCache:
    """Rule engine Redis cache manager."""

    def __init__(self, redis_cache: RedisCache):
        self._redis = redis_cache

    def _make_key(self, tenant_id: Optional[str], shift_type_id: str) -> str:
        """Build cache key for rule set by shift type."""
        tenant_part = f"{tenant_id}:" if tenant_id else ""
        return f"{CACHE_PREFIX}:{tenant_part}ruleset:{shift_type_id}"

    def _make_key_v2(
        self,
        tenant_id: Optional[str],
        shift_type_id: str,
        store_id: Optional[str] = None,
        department_id: Optional[str] = None,
    ) -> str:
        """
        Build cache key for rule set with store/department support.

        新版本缓存 key，支持门店/科室级规则：
        - 如果有 department_id，格式: rule:{tenant_id}:ruleset:{shift_type_id}:dept:{department_id}
        - 如果有 store_id，格式: rule:{tenant_id}:ruleset:{shift_type_id}:store:{store_id}
        - 否则（租户级），格式: rule:{tenant_id}:ruleset:{shift_type_id}
        """
        tenant_part = f"{tenant_id}:" if tenant_id else ""
        if department_id:
            return f"{CACHE_PREFIX}:{tenant_part}ruleset:{shift_type_id}:dept:{department_id}"
        elif store_id:
            return f"{CACHE_PREFIX}:{tenant_part}ruleset:{shift_type_id}:store:{store_id}"
        else:
            return f"{CACHE_PREFIX}:{tenant_part}ruleset:{shift_type_id}"

    async def get_rule_sets(self, tenant_id: Optional[str], shift_type_id: str) -> Optional[List[CachedRuleSet]]:
        """Get cached rule sets for a shift type."""
        key = self._make_key(tenant_id, shift_type_id)
        try:
            data = await self._redis.get(key)
            if data:
                rule_sets_data = json.loads(data)
                return [CachedRuleSet.from_dict(rs) for rs in rule_sets_data]
        except Exception as e:
            logger.warning(f"Cache get failed for key={key}: {e}")
        return None

    async def get_rule_sets_v2(
        self,
        tenant_id: Optional[str],
        shift_type_id: str,
        store_id: Optional[str] = None,
        department_id: Optional[str] = None,
    ) -> Optional[List[CachedRuleSet]]:
        """Get cached rule sets for a shift type with store/department support."""
        key = self._make_key_v2(tenant_id, shift_type_id, store_id, department_id)
        try:
            data = await self._redis.get(key)
            if data:
                rule_sets_data = json.loads(data)
                return [CachedRuleSet.from_dict(rs) for rs in rule_sets_data]
        except Exception as e:
            logger.warning(f"Cache get failed for key={key}: {e}")
        return None

    async def set_rule_sets(
        self,
        tenant_id: Optional[str],
        shift_type_id: str,
        rule_sets: List[CachedRuleSet]
    ) -> None:
        """Cache rule sets for a shift type."""
        key = self._make_key(tenant_id, shift_type_id)
        try:
            serialized = json.dumps([rs.to_dict() for rs in rule_sets], default=str)
            await self._redis.set(key, serialized, ex=CACHE_TTL)
        except Exception as e:
            logger.warning(f"Cache set failed for key={key}: {e}")

    async def set_rule_sets_v2(
        self,
        tenant_id: Optional[str],
        shift_type_id: str,
        store_id: Optional[str],
        department_id: Optional[str],
        rule_sets: List[CachedRuleSet],
    ) -> None:
        """Cache rule sets for a shift type with store/department support."""
        key = self._make_key_v2(tenant_id, shift_type_id, store_id, department_id)
        try:
            serialized = json.dumps([rs.to_dict() for rs in rule_sets], default=str)
            await self._redis.set(key, serialized, ex=CACHE_TTL)
        except Exception as e:
            logger.warning(f"Cache set failed for key={key}: {e}")

    async def invalidate(self, tenant_id: Optional[str], shift_type_ids: List[str]) -> None:
        """
        Invalidate cached rule sets for given shift types.

        注意：这个方法只能失效基础的租户级缓存。
        如果有门店/科室级缓存，需要使用 invalidate_v2 方法。
        """
        for shift_type_id in shift_type_ids:
            key = self._make_key(tenant_id, shift_type_id)
            try:
                await self._redis.delete(key)
            except Exception as e:
                logger.warning(f"Cache invalidation failed for key={key}: {e}")

    async def invalidate_v2(
        self,
        tenant_id: Optional[str],
        shift_type_ids: List[str],
        store_ids: Optional[List[str]] = None,
        department_ids: Optional[List[str]] = None,
    ) -> None:
        """
        Invalidate cached rule sets for given shift types with store/department support.

        当规则组变更时，需要失效所有相关缓存：
        - 基础租户级缓存
        - 所有门店级缓存（如果有 store_ids）
        - 所有科室级缓存（如果有 department_ids）
        """
        # 失效基础租户级缓存
        for shift_type_id in shift_type_ids:
            key = self._make_key(tenant_id, shift_type_id)
            try:
                await self._redis.delete(key)
            except Exception:
                pass

        # 失效门店级缓存
        if store_ids:
            for shift_type_id in shift_type_ids:
                for store_id in store_ids:
                    key = self._make_key_v2(tenant_id, shift_type_id, store_id=store_id)
                    try:
                        await self._redis.delete(key)
                    except Exception:
                        pass

        # 失效科室级缓存
        if department_ids:
            for shift_type_id in shift_type_ids:
                for dept_id in department_ids:
                    key = self._make_key_v2(tenant_id, shift_type_id, department_id=dept_id)
                    try:
                        await self._redis.delete(key)
                    except Exception:
                        pass

    async def invalidate_tenant(self, tenant_id: Optional[str]) -> None:
        """Invalidate all cached rule sets for a tenant (best-effort scan)."""
        tenant_part = f"{tenant_id}:" if tenant_id else ""
        pattern = f"{CACHE_PREFIX}:{tenant_part}ruleset:*"
        try:
            client = await self._get_raw_client()
            cursor = 0
            while True:
                cursor, keys = await client.scan(cursor, match=pattern, count=100)
                if keys:
                    await self._redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception as e:
            logger.warning(f"Tenant cache invalidation failed for pattern={pattern}: {e}")

    @staticmethod
    def _get_raw_client():
        """Helper to get raw Redis client for scan operations."""
        from app.core.redis import get_redis
        return get_redis()
