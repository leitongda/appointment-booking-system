"""
规则引擎性能监控服务

负责收集和分析规则引擎的性能数据，包括：
- 调用频率统计
- 数据库查询延迟监控
- 慢查询日志
- 性能指标聚合（P50、P95、P99）
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from collections import defaultdict
import time

from app.core.redis import RedisCache
from app.core.config import settings

logger = logging.getLogger(__name__)


class RulePerformanceService:
    """规则引擎性能监控服务"""

    # Redis 键前缀
    PREFIX_COUNTER = "rule_engine:counter:"      # 调用计数器
    PREFIX_LATENCY = "rule_engine:latency:"      # 延迟统计
    PREFIX_SLOW_QUERY = "rule_engine:slow:"      # 慢查询日志
    PREFIX_STATS = "rule_engine:stats:"          # 聚合统计

    # 操作类型
    OP_GET_APPLICABLE_RULE_SET = "get_applicable_rule_set"
    OP_CHECK_ACTION_WINDOW = "check_action_window"
    OP_GET_BOOKING_POLICY = "get_booking_policy"
    OP_GET_CHECKIN_POLICY = "get_checkin_policy"
    OP_GET_CAPACITY_POLICY = "get_capacity_policy"
    OP_CHECK_CONFLICTS = "check_booking_conflicts"
    OP_CHECK_CAPACITY = "check_capacity_limits"

    # 默认配置
    DEFAULT_SLOW_QUERY_THRESHOLD = 100  # 慢查询阈值（毫秒）
    DEFAULT_METRICS_TTL = 86400 * 7     # 指标保留时间（7天）
    DEFAULT_SLOW_QUERY_TTL = 86400 * 30 # 慢查询保留时间（30天）

    def __init__(self):
        """初始化性能监控服务"""
        self.enabled = settings.RULE_PERFORMANCE_MONITORING_ENABLED
        self.slow_query_threshold = settings.RULE_SLOW_QUERY_THRESHOLD
        self.metrics_ttl = settings.RULE_METRICS_TTL
        self.slow_query_ttl = settings.RULE_SLOW_QUERY_TTL

    async def record_call(
        self,
        operation: str,
        duration_ms: float,
        shift_type_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        记录规则引擎调用

        Args:
            operation: 操作类型
            duration_ms: 执行耗时（毫秒）
            shift_type_id: 班次类型ID
            metadata: 额外的元数据
        """
        if not self.enabled:
            return

        try:
            # 异步记录，避免阻塞主流程
            record_coro = self._record_call_async(
                operation=operation,
                duration_ms=duration_ms,
                shift_type_id=shift_type_id,
                metadata=metadata
            )
            task = asyncio.create_task(record_coro)
            if asyncio.iscoroutine(task):
                try:
                    await task
                finally:
                    record_coro.close()
            elif not isinstance(task, asyncio.Task):
                record_coro.close()
        except Exception as e:
            logger.error(f"记录性能数据失败: {e}")

    async def _record_call_async(
        self,
        operation: str,
        duration_ms: float,
        shift_type_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """异步记录调用数据"""
        try:
            # 1. 更新调用计数器
            counter_key = f"{self.PREFIX_COUNTER}{operation}"
            await RedisCache.incr(counter_key)
            await RedisCache.set(counter_key, await RedisCache.get(counter_key), self.metrics_ttl)

            # 2. 记录延迟数据（使用有序集合存储延迟值）
            latency_key = f"{self.PREFIX_LATENCY}{operation}"
            client = await RedisCache.get_redis()
            timestamp = int(time.time() * 1000)  # 毫秒时间戳
            await client.zadd(latency_key, {str(timestamp): duration_ms})
            await client.expire(latency_key, self.metrics_ttl)

            # 3. 记录慢查询
            if duration_ms >= self.slow_query_threshold:
                await self._record_slow_query(
                    operation=operation,
                    duration_ms=duration_ms,
                    shift_type_id=shift_type_id,
                    metadata=metadata
                )

        except Exception as e:
            logger.error(f"异步记录性能数据失败: operation={operation}, error={e}")

    async def _record_slow_query(
        self,
        operation: str,
        duration_ms: float,
        shift_type_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """记录慢查询"""
        try:
            slow_query_data = {
                "operation": operation,
                "duration_ms": round(duration_ms, 2),
                "shift_type_id": shift_type_id,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }

            # 使用列表存储慢查询日志
            slow_key = f"{self.PREFIX_SLOW_QUERY}{operation}"
            client = await RedisCache.get_redis()
            await client.lpush(slow_key, json.dumps(slow_query_data, ensure_ascii=False))

            # 限制列表长度，只保留最近的1000条
            await client.ltrim(slow_key, 0, 999)
            await client.expire(slow_key, self.slow_query_ttl)

            # 记录日志
            logger.warning(
                f"规则引擎慢查询: operation={operation}, "
                f"duration={duration_ms:.2f}ms, shift_type_id={shift_type_id}"
            )

        except Exception as e:
            logger.error(f"记录慢查询失败: {e}")

    async def get_performance_stats(
        self,
        operation: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        获取性能统计信息

        Args:
            operation: 操作类型，None 表示获取所有操作
            hours: 统计时间范围（小时）

        Returns:
            性能统计数据
        """
        if not self.enabled:
            return {"enabled": False}

        try:
            operations = [operation] if operation else [
                self.OP_GET_APPLICABLE_RULE_SET,
                self.OP_CHECK_ACTION_WINDOW,
                self.OP_GET_BOOKING_POLICY,
                self.OP_GET_CHECKIN_POLICY,
                self.OP_GET_CAPACITY_POLICY,
                self.OP_CHECK_CONFLICTS,
                self.OP_CHECK_CAPACITY,
            ]

            stats = {}
            for op in operations:
                op_stats = await self._get_operation_stats(op, hours)
                stats[op] = op_stats

            return {
                "enabled": True,
                "stats": stats,
                "summary": self._calculate_summary(stats),
                "query_params": {
                    "operation": operation,
                    "hours": hours
                }
            }

        except Exception as e:
            logger.error(f"获取性能统计失败: {e}")
            return {"error": str(e)}

    async def _get_operation_stats(
        self,
        operation: str,
        hours: int
    ) -> Dict[str, Any]:
        """获取单个操作的统计信息"""
        try:
            # 1. 调用次数
            counter_key = f"{self.PREFIX_COUNTER}{operation}"
            count = await RedisCache.get(counter_key, 0)

            # 2. 延迟统计
            latency_key = f"{self.PREFIX_LATENCY}{operation}"
            client = await RedisCache.get_redis()

            # 获取指定时间范围内的延迟数据
            min_score = int((time.time() - hours * 3600) * 1000)
            max_score = int(time.time() * 1000)
            latency_values = await client.zrangebyscore(
                latency_key, min_score, max_score, withscores=False
            )

            # 计算延迟分位数
            latency_ms = [float(v) for v in latency_values] if latency_values else []
            percentiles = self._calculate_percentiles(latency_ms) if latency_ms else {
                "p50": 0, "p95": 0, "p99": 0, "avg": 0, "max": 0, "min": 0
            }

            # 3. 慢查询数量
            slow_key = f"{self.PREFIX_SLOW_QUERY}{operation}"
            slow_count = await client.llen(slow_key)

            return {
                "count": count,
                "latency_ms": percentiles,
                "slow_query_count": slow_count,
                "avg_rate": round(count / hours, 2) if hours > 0 else 0
            }

        except Exception as e:
            logger.error(f"获取操作统计失败: operation={operation}, error={e}")
            return {
                "count": 0,
                "latency_ms": {},
                "slow_query_count": 0,
                "avg_rate": 0
            }

    def _calculate_percentiles(self, values: List[float]) -> Dict[str, float]:
        """计算延迟分位数"""
        if not values:
            return {"p50": 0, "p95": 0, "p99": 0, "avg": 0, "max": 0, "min": 0}

        sorted_values = sorted(values)
        n = len(sorted_values)

        def get_percentile(p: float) -> float:
            """按百分位位置计算，整数位置取该位，非整数位置线性插值"""
            if n == 1:
                return sorted_values[0]
            rank = (p / 100) * n
            if rank <= 1:
                return sorted_values[0]
            if rank >= n:
                return sorted_values[-1]
            if float(rank).is_integer():
                return sorted_values[int(rank) - 1]
            lower_index = int(rank) - 1
            upper_index = min(lower_index + 1, n - 1)
            weight = rank - int(rank)
            lower_value = sorted_values[lower_index]
            upper_value = sorted_values[upper_index]
            return lower_value + (upper_value - lower_value) * weight

        return {
            "p50": round(get_percentile(50), 2),
            "p95": round(get_percentile(95), 2),
            "p99": round(get_percentile(99), 2),
            "avg": round(sum(sorted_values) / n, 2),
            "max": round(sorted_values[-1], 2),
            "min": round(sorted_values[0], 2)
        }

    def _calculate_summary(self, stats: Dict[str, Dict]) -> Dict[str, Any]:
        """计算总体摘要"""
        total_calls = sum(s.get("count", 0) for s in stats.values())
        total_slow = sum(s.get("slow_query_count", 0) for s in stats.values())

        # 找出最慢的操作
        slowest_op = None
        max_p99 = 0
        for op, data in stats.items():
            p99 = data.get("latency_ms", {}).get("p99", 0)
            if p99 > max_p99:
                max_p99 = p99
                slowest_op = op

        return {
            "total_calls": total_calls,
            "total_slow_queries": total_slow,
            "slowest_operation": slowest_op,
            "slowest_p99": max_p99
        }

    async def get_slow_queries(
        self,
        operation: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取慢查询列表

        Args:
            operation: 操作类型，None 表示获取所有操作
            limit: 返回数量限制

        Returns:
            慢查询列表
        """
        if not self.enabled:
            return []

        try:
            operations = [operation] if operation else [
                self.OP_GET_APPLICABLE_RULE_SET,
                self.OP_CHECK_ACTION_WINDOW,
                self.OP_GET_BOOKING_POLICY,
                self.OP_GET_CHECKIN_POLICY,
                self.OP_GET_CAPACITY_POLICY,
                self.OP_CHECK_CONFLICTS,
                self.OP_CHECK_CAPACITY,
            ]

            all_slow_queries = []
            client = await RedisCache.get_redis()

            for op in operations:
                slow_key = f"{self.PREFIX_SLOW_QUERY}{op}"
                # 获取最近的慢查询
                slow_query_strs = await client.lrange(slow_key, 0, limit - 1)

                for query_str in slow_query_strs:
                    try:
                        query_data = json.loads(query_str)
                        all_slow_queries.append(query_data)
                    except json.JSONDecodeError:
                        continue

            # 按时间倒序排序
            all_slow_queries.sort(
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )

            return all_slow_queries[:limit]

        except Exception as e:
            logger.error(f"获取慢查询失败: {e}")
            return []

    async def clear_metrics(self, operation: Optional[str] = None) -> Dict[str, bool]:
        """
        清除性能指标

        Args:
            operation: 操作类型，None 表示清除所有

        Returns:
            清除结果
        """
        if not self.enabled:
            return {"success": False, "message": "performance monitoring disabled"}

        try:
            operations = [operation] if operation else [
                self.OP_GET_APPLICABLE_RULE_SET,
                self.OP_CHECK_ACTION_WINDOW,
                self.OP_GET_BOOKING_POLICY,
                self.OP_GET_CHECKIN_POLICY,
                self.OP_GET_CAPACITY_POLICY,
                self.OP_CHECK_CONFLICTS,
                self.OP_CHECK_CAPACITY,
            ]

            client = await RedisCache.get_redis()
            deleted = 0

            for op in operations:
                # 删除计数器
                await RedisCache.delete(f"{self.PREFIX_COUNTER}{op}")
                # 删除延迟数据
                await client.delete(f"{self.PREFIX_LATENCY}{op}")
                # 删除慢查询日志
                await client.delete(f"{self.PREFIX_SLOW_QUERY}{op}")
                deleted += 1

            return {
                "success": True,
                "deleted": deleted,
                "message": f"已清除 {deleted} 个操作的指标数据"
            }

        except Exception as e:
            logger.error(f"清除指标失败: {e}")
            return {"success": False, "error": str(e)}


# 全局实例
performance_monitor = RulePerformanceService()
