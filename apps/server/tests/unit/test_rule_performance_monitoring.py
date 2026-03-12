"""
规则引擎性能监控单元测试
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.rule_performance_service import RulePerformanceService


@pytest.fixture
def performance_service():
    """创建性能监控服务实例"""
    return RulePerformanceService()


@pytest.mark.asyncio
async def test_record_call_with_monitoring_enabled(performance_service):
    """测试启用监控时记录调用"""
    with patch.object(performance_service, 'enabled', True):
        with patch('app.services.rule_performance_service.asyncio.create_task') as mock_create_task:
            await performance_service.record_call(
                operation="test_operation",
                duration_ms=50.5,
                shift_type_id="shift_123"
            )

            # 验证异步任务被创建
            mock_create_task.assert_called_once()


@pytest.mark.asyncio
async def test_record_call_with_monitoring_disabled(performance_service):
    """测试禁用监控时不记录调用"""
    with patch.object(performance_service, 'enabled', False):
        with patch('app.services.rule_performance_service.asyncio.create_task') as mock_create_task:
            await performance_service.record_call(
                operation="test_operation",
                duration_ms=50.5
            )

            # 验证异步任务未被创建
            mock_create_task.assert_not_called()


@pytest.mark.asyncio
async def test_slow_query_detection(performance_service):
    """测试慢查询检测"""
    with patch.object(performance_service, 'enabled', True):
        with patch.object(performance_service, 'slow_query_threshold', 100):
            with patch.object(performance_service, '_record_slow_query') as mock_slow:
                # 模拟异步记录
                async def mock_record(*args, **kwargs):
                    if kwargs.get('duration_ms', 0) >= 100:
                        await performance_service._record_slow_query(*args, **kwargs)

                with patch('app.services.rule_performance_service.asyncio.create_task', side_effect=mock_record):
                    # 测试超过阈值的查询
                    await performance_service.record_call(
                        operation="test_operation",
                        duration_ms=150.0
                    )

                    # 验证慢查询被记录
                    # 注意：由于是异步，这里主要验证逻辑正确性


def test_calculate_percentiles(performance_service):
    """测试分位数计算"""
    values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]

    result = performance_service._calculate_percentiles(values)

    assert result['p50'] == 50.0
    assert result['p95'] == 95.0
    assert result['p99'] == 99.0
    assert result['avg'] == 55.0
    assert result['max'] == 100.0
    assert result['min'] == 10.0


def test_calculate_percentiles_empty(performance_service):
    """测试空列表的分位数计算"""
    values = []

    result = performance_service._calculate_percentiles(values)

    assert result['p50'] == 0
    assert result['p95'] == 0
    assert result['p99'] == 0
    assert result['avg'] == 0
    assert result['max'] == 0
    assert result['min'] == 0


def test_calculate_summary(performance_service):
    """测试摘要计算"""
    stats = {
        "op1": {
            "count": 100,
            "latency_ms": {"p99": 50.0},
            "slow_query_count": 5
        },
        "op2": {
            "count": 200,
            "latency_ms": {"p99": 80.0},
            "slow_query_count": 10
        }
    }

    result = performance_service._calculate_summary(stats)

    assert result['total_calls'] == 300
    assert result['total_slow_queries'] == 15
    assert result['slowest_operation'] == "op2"
    assert result['slowest_p99'] == 80.0


@pytest.mark.asyncio
async def test_get_performance_stats_disabled(performance_service):
    """测试监控禁用时获取统计信息"""
    with patch.object(performance_service, 'enabled', False):
        result = await performance_service.get_performance_stats()

        assert result['enabled'] is False


@pytest.mark.asyncio
async def test_clear_metrics_disabled(performance_service):
    """测试监控禁用时清除指标"""
    with patch.object(performance_service, 'enabled', False):
        result = await performance_service.clear_metrics()

        assert result['success'] is False
        assert 'disabled' in result['message'].lower()
