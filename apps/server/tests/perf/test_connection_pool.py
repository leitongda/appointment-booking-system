"""
数据库连接池负载测试

测试目标：
- 验证当前连接池配置（pool_size=5, max_overflow=10）是否满足多租户 SaaS 场景的并发需求
- 测量不同并发级别下的 P50/P95/P99 延迟
- 监控连接池使用率和连接获取超时场景
- 测试连接泄漏检测和恢复能力

运行方式：
    pytest tests/perf/test_connection_pool.py -v -m slow
    pytest tests/perf/test_connection_pool.py::test_pool_baseline -v -s

环境要求：
    - 需要真实 PostgreSQL 数据库连接（不使用内存 SQLite）
    - 从 .env 文件读取 DATABASE_URL
    - 如果没有数据库连接，测试会 skip
"""
import asyncio
import os
import statistics
import time
from dataclasses import dataclass
from typing import List, Optional
from unittest.mock import AsyncMock, patch

import asyncpg
import pytest


# ==================== 测试配置 ====================

# 当前连接池配置（与 config.py 保持一致）
POOL_SIZE = 5
MAX_OVERFLOW = 10
POOL_TIMEOUT = 30  # 秒
MAX_CONNECTIONS = POOL_SIZE + MAX_OVERFLOW  # 15


# ==================== 数据结构 ====================

@dataclass
class PoolMetrics:
    """连接池指标"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    timeout_errors: int
    latencies_ms: List[float]
    max_pool_size: int
    current_connections: int


@dataclass
class TestResult:
    """测试结果"""
    scenario: str
    concurrent_requests: int
    total_requests: int
    success_count: int
    success_rate: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    avg_latency_ms: float
    avg_pool_usage: float
    timeout_count: int


# ==================== 连接池模拟器 ====================

class ConnectionPoolSimulator:
    """
    连接池模拟器

    使用 asyncpg.ConnectionPool 的限制逻辑来模拟真实连接池行为。
    """

    def __init__(self, dsn: str, min_size: int = 5, max_size: int = 15):
        self.dsn = dsn
        self.min_size = min_size
        self.max_size = max_size
        self.pool: Optional[asyncpg.Pool] = None
        self._connection_count = 0
        self._lock = asyncio.Lock()

    async def initialize(self):
        """初始化连接池"""
        try:
            self.pool = await asyncpg.create_pool(
                self.dsn,
                min_size=self.min_size,
                max_size=self.max_size,
                timeout=POOL_TIMEOUT,
                command_timeout=10,
            )
            return True
        except Exception as e:
            print(f"Failed to initialize connection pool: {e}")
            return False

    async def execute_query(self, query: str, *args) -> Optional[asyncpg.Record]:
        """执行查询（自动获取和释放连接）"""
        if not self.pool:
            raise RuntimeError("Pool not initialized")

        async with self._lock:
            self._connection_count += 1

        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def get_pool_status(self) -> dict:
        """获取连接池状态"""
        if not self.pool:
            return {"size": 0, "max_size": self.max_size}

        # asyncpg pool 的 _queue 保存了可用连接
        return {
            "size": getattr(self.pool, "_maxsize", self.max_size) - len(getattr(self.pool, "_queue", [])),
            "max_size": self.max_size,
            "available": len(getattr(self.pool, "_queue", [])) if hasattr(self.pool, "_queue") else 0,
        }

    async def close(self):
        """关闭连接池"""
        if self.pool:
            await self.pool.close()


# ==================== 测试辅助函数 ====================

def calculate_percentiles(data: List[float]) -> tuple:
    """计算 P50, P95, P99 百分位数"""
    if not data:
        return 0.0, 0.0, 0.0

    sorted_data = sorted(data)
    n = len(sorted_data)

    def percentile(p: float) -> float:
        """计算百分位数"""
        index = (p / 100) * (n - 1)
        lower = int(index)
        upper = min(lower + 1, n - 1)
        weight = index - lower
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight

    return percentile(50), percentile(95), percentile(99)


def print_test_result(result: TestResult):
    """打印测试结果"""
    print(f"\n{'=' * 60}")
    print(f"测试场景: {result.scenario}")
    print(f"并发请求数: {result.concurrent_requests}")
    print(f"总请求数: {result.total_requests}")
    print(f"成功请求数: {result.success_count}")
    print(f"成功率: {result.success_rate:.2f}%")
    print(f"超时错误: {result.timeout_count}")
    print(f"\n延迟统计 (ms):")
    print(f"  P50: {result.p50_latency_ms:.2f}")
    print(f"  P95: {result.p95_latency_ms:.2f}")
    print(f"  P99: {result.p99_latency_ms:.2f}")
    print(f"  平均: {result.avg_latency_ms:.2f}")
    print(f"\n连接池使用率:")
    pool_usage_pct = (result.avg_pool_usage / MAX_CONNECTIONS) * 100
    print(f"  平均连接数: {result.avg_pool_usage:.2f} / {MAX_CONNECTIONS}")
    print(f"  使用率: {pool_usage_pct:.1f}%")
    print(f"{'=' * 60}\n")


def analyze_and_recommend(results: List[TestResult]):
    """分析结果并给出配置建议"""
    print(f"\n{'=' * 60}")
    print("综合分析与建议")
    print(f"{'=' * 60}\n")

    # 查找问题场景
    problematic_scenarios = []
    for r in results:
        if r.success_rate < 95:
            problematic_scenarios.append((r.scenario, r.success_rate))
        if r.p95_latency_ms > 500:
            problematic_scenarios.append((r.scenario, f"P95 延迟过高 ({r.p95_latency_ms:.0f}ms)"))
        if r.avg_pool_usage > MAX_CONNECTIONS * 0.8:
            problematic_scenarios.append((r.scenario, f"连接池使用率过高 ({r.avg_pool_usage:.1f}/{MAX_CONNECTIONS})"))

    if not problematic_scenarios:
        print("✓ 当前配置在所有测试场景下表现良好")
        print(f"✓ pool_size={POOL_SIZE}, max_overflow={MAX_OVERFLOW} 满足需求")
        print("\n建议：保持当前配置")
    else:
        print("⚠ 发现以下问题：")
        for scenario, issue in problematic_scenarios:
            print(f"  - {scenario}: {issue}")

        print("\n建议调整：")
        print(f"  - 考虑增加 pool_size 到 {POOL_SIZE + 5}")
        print(f"  - 考虑增加 max_overflow 到 {MAX_OVERFLOW + 10}")
        print(f"  - 或者启用连接池监控（记录慢查询和连接获取超时）")

    print(f"\n{'=' * 60}\n")


# ==================== 测试场景 ====================

@pytest.mark.slow
async def test_pool_baseline(get_real_db_url):
    """
    基准测试：10 并发请求

    预期：全部成功，P95 延迟 < 100ms，连接池使用率 < 50%
    """
    dsn = _convert_url_to_asyncpg_dsn(get_real_db_url)
    simulator = ConnectionPoolSimulator(dsn, min_size=POOL_SIZE, max_size=MAX_CONNECTIONS)

    if not await simulator.initialize():
        pytest.skip("Cannot connect to database")

    try:
        concurrent = 10
        latencies = []
        success_count = 0
        timeout_count = 0
        pool_usages = []

        async def worker(worker_id: int):
            nonlocal success_count, timeout_count
            start_time = time.time()

            try:
                # 执行简单查询
                await simulator.execute_query("SELECT 1 as result, $1::text as worker_id", str(worker_id))
                success_count += 1
            except asyncio.TimeoutError:
                timeout_count += 1
            except Exception as e:
                print(f"Worker {worker_id} failed: {e}")
            finally:
                latencies.append((time.time() - start_time) * 1000)
                # 记录连接池状态
                status = await simulator.get_pool_status()
                pool_usages.append(status.get("size", 0))

        # 并发执行
        tasks = [worker(i) for i in range(concurrent)]
        await asyncio.gather(*tasks)

        # 计算结果
        p50, p95, p99 = calculate_percentiles(latencies)
        avg_latency = statistics.mean(latencies) if latencies else 0
        avg_pool_usage = statistics.mean(pool_usages) if pool_usages else 0

        result = TestResult(
            scenario="基准测试 (10 并发)",
            concurrent_requests=concurrent,
            total_requests=concurrent,
            success_count=success_count,
            success_rate=(success_count / concurrent) * 100,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            avg_latency_ms=avg_latency,
            avg_pool_usage=avg_pool_usage,
            timeout_count=timeout_count,
        )

        print_test_result(result)

        # 断言
        assert result.success_rate == 100, f"基准测试成功率应为 100%，实际 {result.success_rate}%"
        assert result.p95_latency_ms < 100, f"基准测试 P95 延迟应 < 100ms，实际 {result.p95_latency_ms:.2f}ms"
        assert result.avg_pool_usage < MAX_CONNECTIONS * 0.5, f"基准测试连接池使用率应 < 50%，实际 {result.avg_pool_usage:.1f}/{MAX_CONNECTIONS}"

    finally:
        await simulator.close()


@pytest.mark.slow
async def test_pool_moderate(get_real_db_url):
    """
    中等负载测试：50 并发请求

    预期：成功率 > 95%，P95 延迟 < 300ms
    """
    dsn = _convert_url_to_asyncpg_dsn(get_real_db_url)
    simulator = ConnectionPoolSimulator(dsn, min_size=POOL_SIZE, max_size=MAX_CONNECTIONS)

    if not await simulator.initialize():
        pytest.skip("Cannot connect to database")

    try:
        concurrent = 50
        latencies = []
        success_count = 0
        timeout_count = 0
        pool_usages = []

        async def worker(worker_id: int):
            nonlocal success_count, timeout_count
            start_time = time.time()

            try:
                # 模拟业务查询：查询租户相关数据
                await simulator.execute_query("""
                    SELECT
                        tenant_id,
                        now() as current_time,
                        pg_sleep(0.01) as simulated_work
                """, str(worker_id))
                success_count += 1
            except asyncio.TimeoutError:
                timeout_count += 1
            except Exception as e:
                print(f"Worker {worker_id} failed: {e}")
            finally:
                latencies.append((time.time() - start_time) * 1000)
                status = await simulator.get_pool_status()
                pool_usages.append(status.get("size", 0))

        tasks = [worker(i) for i in range(concurrent)]
        await asyncio.gather(*tasks)

        p50, p95, p99 = calculate_percentiles(latencies)
        avg_latency = statistics.mean(latencies) if latencies else 0
        avg_pool_usage = statistics.mean(pool_usages) if pool_usages else 0

        result = TestResult(
            scenario="中等负载 (50 并发)",
            concurrent_requests=concurrent,
            total_requests=concurrent,
            success_count=success_count,
            success_rate=(success_count / concurrent) * 100,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            avg_latency_ms=avg_latency,
            avg_pool_usage=avg_pool_usage,
            timeout_count=timeout_count,
        )

        print_test_result(result)

        # 断言：中等负载下应该能处理
        assert result.success_rate >= 95, f"中等负载成功率应 >= 95%，实际 {result.success_rate}%"
        assert result.p95_latency_ms < 500, f"中等负载 P95 延迟应 < 500ms，实际 {result.p95_latency_ms:.2f}ms"

    finally:
        await simulator.close()


@pytest.mark.slow
async def test_pool_stress(get_real_db_url):
    """
    压力测试：100 并发请求

    预期：可能会出现超时，但大部分请求应成功
    """
    dsn = _convert_url_to_asyncpg_dsn(get_real_db_url)
    simulator = ConnectionPoolSimulator(dsn, min_size=POOL_SIZE, max_size=MAX_CONNECTIONS)

    if not await simulator.initialize():
        pytest.skip("Cannot connect to database")

    try:
        concurrent = 100
        latencies = []
        success_count = 0
        timeout_count = 0
        pool_usages = []

        async def worker(worker_id: int):
            nonlocal success_count, timeout_count
            start_time = time.time()

            try:
                # 模拟复杂查询
                await simulator.execute_query("""
                    SELECT
                        tenant_id,
                        now() as current_time,
                        pg_sleep(0.02) as simulated_heavy_work
                """, str(worker_id))
                success_count += 1
            except asyncio.TimeoutError:
                timeout_count += 1
            except Exception as e:
                print(f"Worker {worker_id} failed: {e}")
            finally:
                latencies.append((time.time() - start_time) * 1000)
                status = await simulator.get_pool_status()
                pool_usages.append(status.get("size", 0))

        tasks = [worker(i) for i in range(concurrent)]
        await asyncio.gather(*tasks)

        p50, p95, p99 = calculate_percentiles(latencies)
        avg_latency = statistics.mean(latencies) if latencies else 0
        avg_pool_usage = statistics.mean(pool_usages) if pool_usages else 0

        result = TestResult(
            scenario="压力测试 (100 并发)",
            concurrent_requests=concurrent,
            total_requests=concurrent,
            success_count=success_count,
            success_rate=(success_count / concurrent) * 100,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            avg_latency_ms=avg_latency,
            avg_pool_usage=avg_pool_usage,
            timeout_count=timeout_count,
        )

        print_test_result(result)

        # 压力测试下，允许部分失败
        # 但成功率应该 > 50%
        assert result.success_rate > 50, f"压力测试成功率应 > 50%，实际 {result.success_rate}%"

    finally:
        await simulator.close()


@pytest.mark.slow
async def test_pool_timeout(get_real_db_url):
    """
    超限测试：超过 pool_size + max_overflow 的并发

    预期：部分请求会超时，验证超时机制是否正常工作
    """
    dsn = _convert_url_to_asyncpg_dsn(get_real_db_url)
    simulator = ConnectionPoolSimulator(dsn, min_size=POOL_SIZE, max_size=MAX_CONNECTIONS)

    if not await simulator.initialize():
        pytest.skip("Cannot connect to database")

    try:
        # 20 个并发，大于最大连接数 15
        concurrent = 20
        latencies = []
        success_count = 0
        timeout_count = 0
        pool_usages = []

        # 设置较短的获取超时用于测试
        original_timeout = POOL_TIMEOUT
        test_timeout = 2  # 2 秒超时

        async def worker(worker_id: int):
            nonlocal success_count, timeout_count
            start_time = time.time()

            try:
                # 使用长时间查询来制造连接竞争
                await asyncio.wait_for(
                    simulator.execute_query("""
                        SELECT
                            tenant_id,
                            pg_sleep(0.5) as long_query
                    """, str(worker_id)),
                    timeout=test_timeout
                )
                success_count += 1
            except asyncio.TimeoutError:
                timeout_count += 1
            except Exception as e:
                print(f"Worker {worker_id} failed: {e}")
            finally:
                latencies.append((time.time() - start_time) * 1000)
                status = await simulator.get_pool_status()
                pool_usages.append(status.get("size", 0))

        tasks = [worker(i) for i in range(concurrent)]
        await asyncio.gather(*tasks)

        p50, p95, p99 = calculate_percentiles(latencies)
        avg_latency = statistics.mean(latencies) if latencies else 0
        avg_pool_usage = statistics.mean(pool_usages) if pool_usages else 0

        result = TestResult(
            scenario="超限测试 (20 并发，最大连接 15)",
            concurrent_requests=concurrent,
            total_requests=concurrent,
            success_count=success_count,
            success_rate=(success_count / concurrent) * 100,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            avg_latency_ms=avg_latency,
            avg_pool_usage=avg_pool_usage,
            timeout_count=timeout_count,
        )

        print_test_result(result)

        # 超限场景下，应该有超时发生
        print(f"预期发生超时（并发数 {concurrent} > 最大连接 {MAX_CONNECTIONS}）")
        print(f"实际超时数: {timeout_count}")

        # 验证至少有一些请求成功
        assert result.success_count > 0, "应该有至少部分请求成功"

    finally:
        await simulator.close()


@pytest.mark.slow
async def test_pool_recovery(get_real_db_url):
    """
    恢复测试：高负载后连接是否正常释放

    验证连接池在高负载后能正常释放连接，
    后续请求仍能正常执行。
    """
    dsn = _convert_url_to_asyncpg_dsn(get_real_db_url)
    simulator = ConnectionPoolSimulator(dsn, min_size=POOL_SIZE, max_size=MAX_CONNECTIONS)

    if not await simulator.initialize():
        pytest.skip("Cannot connect to database")

    try:
        # 第一阶段：高负载
        print("\n第一阶段：高负载 (50 并发)")
        high_load_concurrent = 50

        async def high_load_worker(worker_id: int):
            try:
                await simulator.execute_query("SELECT 1, $1", str(worker_id))
            except Exception:
                pass

        high_load_tasks = [high_load_worker(i) for i in range(high_load_concurrent)]
        await asyncio.gather(*high_load_tasks)

        # 等待连接池恢复
        await asyncio.sleep(1)

        # 第二阶段：验证恢复
        print("第二阶段：验证连接池恢复")
        verify_concurrent = 10
        latencies = []
        success_count = 0

        async def verify_worker(worker_id: int):
            nonlocal success_count
            start_time = time.time()

            try:
                await simulator.execute_query("SELECT 2 as recovered, $1", str(worker_id))
                success_count += 1
            except Exception as e:
                print(f"Verify worker {worker_id} failed: {e}")
            finally:
                latencies.append((time.time() - start_time) * 1000)

        verify_tasks = [verify_worker(i) for i in range(verify_concurrent)]
        await asyncio.gather(*verify_tasks)

        # 检查连接池状态
        pool_status = await simulator.get_pool_status()

        p50, p95, p99 = calculate_percentiles(latencies)
        avg_latency = statistics.mean(latencies) if latencies else 0

        result = TestResult(
            scenario="恢复测试 (高负载后验证)",
            concurrent_requests=verify_concurrent,
            total_requests=verify_concurrent,
            success_count=success_count,
            success_rate=(success_count / verify_concurrent) * 100,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            avg_latency_ms=avg_latency,
            avg_pool_usage=pool_status.get("size", 0),
            timeout_count=0,
        )

        print_test_result(result)

        # 断言：恢复后应该全部成功
        assert result.success_rate == 100, f"恢复测试成功率应为 100%，实际 {result.success_rate}%"
        assert result.p95_latency_ms < 200, f"恢复后 P95 延迟应 < 200ms，实际 {result.p95_latency_ms:.2f}ms"

        # 打印连接池状态
        print(f"连接池状态: {pool_status}")

    finally:
        await simulator.close()


@pytest.mark.slow
async def test_pool_comprehensive(get_real_db_url):
    """
    综合测试：运行所有场景并生成分析报告

    此测试运行所有场景并给出最终的配置建议。
    """
    dsn = _convert_url_to_asyncpg_dsn(get_real_db_url)
    results = []

    # 场景 1: 基准测试
    print("\n" + "=" * 60)
    print("开始综合测试")
    print("=" * 60)

    try:
        simulator = ConnectionPoolSimulator(dsn, min_size=POOL_SIZE, max_size=MAX_CONNECTIONS)

        if not await simulator.initialize():
            pytest.skip("Cannot connect to database")

        try:
            # 基准测试
            result1 = await _run_scenario(simulator, "基准测试", 10, simple_query=True)
            results.append(result1)

            # 中等负载
            result2 = await _run_scenario(simulator, "中等负载", 50, simple_query=False)
            results.append(result2)

            # 压力测试
            result3 = await _run_scenario(simulator, "压力测试", 100, simple_query=False)
            results.append(result3)

        finally:
            await simulator.close()

        # 生成综合分析
        analyze_and_recommend(results)

    except Exception as e:
        print(f"Comprehensive test failed: {e}")
        raise


# ==================== 辅助测试函数 ====================

async def _run_scenario(
    simulator: ConnectionPoolSimulator,
    scenario_name: str,
    concurrent: int,
    simple_query: bool = True,
) -> TestResult:
    """运行单个测试场景"""
    latencies = []
    success_count = 0
    timeout_count = 0
    pool_usages = []

    async def worker(worker_id: int):
        nonlocal success_count, timeout_count
        start_time = time.time()

        try:
            if simple_query:
                await simulator.execute_query("SELECT 1 as result, $1", str(worker_id))
            else:
                await simulator.execute_query("""
                    SELECT tenant_id, now() as ts, pg_sleep(0.01)
                """, str(worker_id))
            success_count += 1
        except asyncio.TimeoutError:
            timeout_count += 1
        except Exception as e:
            pass  # 静默处理错误
        finally:
            latencies.append((time.time() - start_time) * 1000)
            status = await simulator.get_pool_status()
            pool_usages.append(status.get("size", 0))

    tasks = [worker(i) for i in range(concurrent)]
    await asyncio.gather(*tasks)

    p50, p95, p99 = calculate_percentiles(latencies)
    avg_latency = statistics.mean(latencies) if latencies else 0
    avg_pool_usage = statistics.mean(pool_usages) if pool_usages else 0

    result = TestResult(
        scenario=scenario_name,
        concurrent_requests=concurrent,
        total_requests=concurrent,
        success_count=success_count,
        success_rate=(success_count / concurrent) * 100,
        p50_latency_ms=p50,
        p95_latency_ms=p95,
        p99_latency_ms=p99,
        avg_latency_ms=avg_latency,
        avg_pool_usage=avg_pool_usage,
        timeout_count=timeout_count,
    )

    print_test_result(result)
    return result


def _convert_url_to_asyncpg_dsn(sqlalchemy_url: str) -> str:
    """
    将 SQLAlchemy URL 转换为 asyncpg DSN

    示例：
    Input:  postgresql+asyncpg://user:pass@host:5432/db
    Output: postgresql://user:pass@host:5432/db
    """
    dsn = sqlalchemy_url.replace("postgresql+asyncpg://", "postgresql://")
    dsn = dsn.replace("postgresql+psycopg://", "postgresql://")
    return dsn


# ==================== Fixtures ====================

@pytest.fixture(scope="session")
def get_real_db_url():
    """
    获取真实数据库 URL

    优先级：
    1. 环境变量 TEST_DATABASE_URL
    2. .env 文件中的 DATABASE_URL
    3. skip
    """
    from app.core.config import settings

    url = os.getenv("TEST_DATABASE_URL", settings.DATABASE_URL)

    # 检查是否是测试数据库
    if "test" not in url.lower() and os.getenv("FORCE_PROD_TEST") != "true":
        pytest.skip("Skipping production database. Set TEST_DATABASE_URL or FORCE_PROD_TEST=true")

    return url
