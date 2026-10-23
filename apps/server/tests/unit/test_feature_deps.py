"""require_feature 功能开关依赖单元测试（R3-5）

覆盖：
- 总开关 FEATURE_ENFORCEMENT_ENABLED=False 时放行
- 租户未开通 → 403
- 租户已开通 → 放行
- 平台管理员（tenant_id 为空）不受限
"""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.common.feature_deps import require_feature
from app.core.config import settings


@pytest.mark.unit
class TestRequireFeature:
    """require_feature(feature) 依赖工厂"""

    async def test_total_switch_off_allows_everything(self):
        """总开关关闭时不拦截，也不查库"""
        checker = require_feature("basic_statistics")
        db = AsyncMock()

        with patch.object(settings, "FEATURE_ENFORCEMENT_ENABLED", False), patch(
            "app.common.feature_deps.FeatureFlagService.is_enabled",
            new=AsyncMock(return_value=False),
        ) as is_enabled:
            result = await checker(current_admin={"tenant_id": "tenant-1"}, db=db)

        assert result is None
        is_enabled.assert_not_awaited()

    async def test_disabled_feature_raises_403(self):
        """租户未开通功能 → 403"""
        checker = require_feature("export_data")

        with patch.object(settings, "FEATURE_ENFORCEMENT_ENABLED", True), patch(
            "app.common.feature_deps.FeatureFlagService.is_enabled",
            new=AsyncMock(return_value=False),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await checker(current_admin={"tenant_id": "tenant-1"}, db=AsyncMock())

        assert exc_info.value.status_code == 403
        assert "export_data" in exc_info.value.detail

    async def test_enabled_feature_passes(self):
        """租户已开通功能 → 放行"""
        checker = require_feature("basic_statistics")

        with patch.object(settings, "FEATURE_ENFORCEMENT_ENABLED", True), patch(
            "app.common.feature_deps.FeatureFlagService.is_enabled",
            new=AsyncMock(return_value=True),
        ) as is_enabled:
            result = await checker(current_admin={"tenant_id": "tenant-1"}, db=AsyncMock())

        assert result is None
        is_enabled.assert_awaited_once()

    async def test_platform_admin_is_not_restricted(self):
        """平台管理员（tenant_id 为空）不受租户开关限制，也不查库"""
        checker = require_feature("export_data")

        with patch.object(settings, "FEATURE_ENFORCEMENT_ENABLED", True), patch(
            "app.common.feature_deps.FeatureFlagService.is_enabled",
            new=AsyncMock(return_value=False),
        ) as is_enabled:
            result = await checker(current_admin={"tenant_id": None}, db=AsyncMock())

        assert result is None
        is_enabled.assert_not_awaited()
