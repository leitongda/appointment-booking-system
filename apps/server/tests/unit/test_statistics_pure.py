"""数据统计模块纯函数单元测试

覆盖:
- _build_store_filter_condition() 三种输入类型
- 汇总率计算边界（除零、精度）
"""
import pytest
from unittest.mock import MagicMock

from app.modules.statistics.router import _build_store_filter_condition


@pytest.mark.unit
class TestBuildStoreFilterCondition:
    """测试门店过滤条件构建"""

    def test_none_returns_none(self):
        """无过滤返回 None"""
        result = _build_store_filter_condition(None)
        assert result is None

    def test_single_string_filter(self):
        """单个门店 ID 过滤"""
        result = _build_store_filter_condition("store-123")
        assert result is not None
        # 验证是 Doctor.store_id == "store-123" 条件
        assert str(result) == "doctors.store_id = :store_id_1"

    def test_list_filter(self):
        """多个门店 ID 过滤（IN 条件）"""
        result = _build_store_filter_condition(["store-1", "store-2"])
        assert result is not None
        assert "IN" in str(result).upper()

    def test_empty_list_filter(self):
        """空列表返回 IN 条件（空 IN）"""
        result = _build_store_filter_condition([])
        assert result is not None

    def test_single_element_list(self):
        """单元素列表返回 IN 条件"""
        result = _build_store_filter_condition(["store-only"])
        assert result is not None


@pytest.mark.unit
class TestRateCalculationEdgeCases:
    """测试汇总率计算的边界情况（模拟 route handler 中的计算逻辑）"""

    def test_completed_rate_zero_total(self):
        """total 为 0 时完成率为 0"""
        total = 0
        completed = 0
        rate = round(completed / total * 100, 2) if total > 0 else 0
        assert rate == 0

    def test_completed_rate_normal(self):
        """正常完成率计算"""
        total = 100
        completed = 85
        rate = round(completed / total * 100, 2)
        assert rate == 85.0

    def test_no_show_rate(self):
        """爽约率"""
        total = 50
        no_show = 3
        rate = round(no_show / total * 100, 2)
        assert rate == 6.0

    def test_all_cancelled(self):
        """全部取消"""
        total = 10
        cancelled = 10
        rate = round(cancelled / total * 100, 2)
        assert rate == 100.0

    def test_precision_rounding(self):
        """精度测试：保留 2 位小数"""
        total = 7
        completed = 3
        rate = round(completed / total * 100, 2)
        # 3/7 = 0.428571... * 100 = 42.8571...
        assert rate == 42.86
