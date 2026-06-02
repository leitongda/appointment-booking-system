"""低代码功能门禁服务单元测试。

测试 LowCodeFeatureGate 的功能开关检查、页面配额检查，
以及 enforce_* 方法的 403 异常抛出。
"""

import pytest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.modules.lowcode.feature_gate import LowCodeFeatureGate


@pytest.fixture
def mock_db():
    """异步数据库会话 mock"""
    return AsyncMock()


@pytest.fixture
def gate(mock_db):
    """LowCodeFeatureGate 实例"""
    return LowCodeFeatureGate(mock_db)


# ------------------------------------------------------------------
# check_feature
# ------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
async def test_check_feature_enabled(gate):
    """功能开关开启时返回 True"""
    with patch(
        "app.modules.lowcode.feature_gate.FeatureFlagService.is_enabled",
        new_callable=AsyncMock,
        return_value=True,
    ):
        result = await gate.check_feature("tenant-1", "lowcode_advanced_components")

    assert result is True


@pytest.mark.asyncio
@pytest.mark.unit
async def test_check_feature_disabled(gate):
    """功能开关关闭时返回 False"""
    with patch(
        "app.modules.lowcode.feature_gate.FeatureFlagService.is_enabled",
        new_callable=AsyncMock,
        return_value=False,
    ):
        result = await gate.check_feature("tenant-1", "lowcode_advanced_components")

    assert result is False


@pytest.mark.asyncio
@pytest.mark.unit
async def test_check_feature_lowcode_basic_default_true(gate):
    """lowcode_basic 默认为 True（向后兼容）"""
    # 不 mock is_enabled，让 get_default_features 返回真实默认值
    with patch(
        "app.modules.lowcode.feature_gate.FeatureFlagService.is_enabled",
        new_callable=AsyncMock,
        side_effect=lambda _db, _tenant_id, feature_name: feature_name == "lowcode_basic",
    ):
        result = await gate.check_feature("tenant-1", "lowcode_basic")

    assert result is True


# ------------------------------------------------------------------
# check_page_limit
# ------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
async def test_check_page_limit_under_limit(gate):
    """页面数未达上限时返回 (True, current, max)"""
    with patch(
        "app.modules.lowcode.feature_gate.FeatureFlagService.get_tenant_features",
        new_callable=AsyncMock,
        return_value={"lowcode_max_pages": 5},
    ):
        gate.db.scalar = AsyncMock(return_value=3)
        allowed, current, max_limit = await gate.check_page_limit("tenant-1")

    assert allowed is True
    assert current == 3
    assert max_limit == 5


@pytest.mark.asyncio
@pytest.mark.unit
async def test_check_page_limit_at_limit(gate):
    """页面数达到上限时返回 (False, current, max)"""
    with patch(
        "app.modules.lowcode.feature_gate.FeatureFlagService.get_tenant_features",
        new_callable=AsyncMock,
        return_value={"lowcode_max_pages": 5},
    ):
        gate.db.scalar = AsyncMock(return_value=5)
        allowed, current, max_limit = await gate.check_page_limit("tenant-1")

    assert allowed is False
    assert current == 5
    assert max_limit == 5


# ------------------------------------------------------------------
# enforce_feature
# ------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
async def test_enforce_feature_raises_403_when_disabled(gate):
    """功能未启用时 enforce_feature 抛出 403"""
    with patch(
        "app.modules.lowcode.feature_gate.FeatureFlagService.is_enabled",
        new_callable=AsyncMock,
        return_value=False,
    ):
        with pytest.raises(HTTPException) as exc_info:
            await gate.enforce_feature("tenant-1", "lowcode_advanced_components")

    assert exc_info.value.status_code == 403
    assert "lowcode_advanced_components" in exc_info.value.detail


@pytest.mark.asyncio
@pytest.mark.unit
async def test_enforce_feature_passes_when_enabled(gate):
    """功能已启用时 enforce_feature 不抛出异常"""
    with patch(
        "app.modules.lowcode.feature_gate.FeatureFlagService.is_enabled",
        new_callable=AsyncMock,
        return_value=True,
    ):
        # 不应抛出异常
        await gate.enforce_feature("tenant-1", "lowcode_advanced_components")


# ------------------------------------------------------------------
# enforce_page_limit
# ------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.unit
async def test_enforce_page_limit_raises_403_at_limit(gate):
    """页面数达上限时 enforce_page_limit 抛出 403"""
    with patch(
        "app.modules.lowcode.feature_gate.FeatureFlagService.get_tenant_features",
        new_callable=AsyncMock,
        return_value={"lowcode_max_pages": 5},
    ):
        gate.db.scalar = AsyncMock(return_value=5)
        with pytest.raises(HTTPException) as exc_info:
            await gate.enforce_page_limit("tenant-1")

    assert exc_info.value.status_code == 403
    assert "5/5" in exc_info.value.detail


@pytest.mark.asyncio
@pytest.mark.unit
async def test_enforce_page_limit_passes_under_limit(gate):
    """页面数未达上限时 enforce_page_limit 不抛出异常"""
    with patch(
        "app.modules.lowcode.feature_gate.FeatureFlagService.get_tenant_features",
        new_callable=AsyncMock,
        return_value={"lowcode_max_pages": 5},
    ):
        gate.db.scalar = AsyncMock(return_value=3)
        # 不应抛出异常
        await gate.enforce_page_limit("tenant-1")
