"""测试通知重试功能"""
import pytest
from datetime import datetime, timedelta
from app.modules.notification_logs.service import calculate_next_retry


class TestCalculateNextRetry:
    """测试下次重试时间计算"""

    def test_first_retry(self):
        """第一次重试应在1分钟后"""
        result = calculate_next_retry(0)
        assert result is not None
        expected = datetime.utcnow() + timedelta(minutes=1)
        # 允许1秒误差
        assert abs((result - expected).total_seconds()) < 1

    def test_second_retry(self):
        """第二次重试应在5分钟后"""
        result = calculate_next_retry(1)
        assert result is not None
        expected = datetime.utcnow() + timedelta(minutes=5)
        assert abs((result - expected).total_seconds()) < 1

    def test_third_retry(self):
        """第三次重试应在30分钟后"""
        result = calculate_next_retry(2)
        assert result is not None
        expected = datetime.utcnow() + timedelta(minutes=30)
        assert abs((result - expected).total_seconds()) < 1

    def test_exceed_max_retries(self):
        """超过最大重试次数应返回None"""
        result = calculate_next_retry(3)
        assert result is None

        result = calculate_next_retry(10)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
