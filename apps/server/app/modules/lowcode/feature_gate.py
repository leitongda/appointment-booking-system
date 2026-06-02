"""低代码平台功能门禁服务。

基于 FeatureFlagService 和订阅计划，检查租户是否有权使用
指定的低代码功能，以及页面配额是否超限。
"""

from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.feature_flags import FeatureFlagService
from app.core.error_codes import ErrorCode
from app.models.lowcode_page import LowCodePage


class LowCodeFeatureGate:
    """低代码功能门禁。

    职责:
    - 检查租户是否启用了指定的低code_* 功能开关
    - 检查/强制执行页面数量配额上限
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Feature flag checks
    # ------------------------------------------------------------------

    async def check_feature(self, tenant_id: str, feature_name: str) -> bool:
        """检查租户是否启用了指定功能。

        feature_name 应为 TenantFeatures 中定义的 lowcode_* 字段名，
        例如 ``lowcode_advanced_components``。

        Args:
            tenant_id: 租户 ID。
            feature_name: 功能开关名称（需以 ``lowcode_`` 开头）。

        Returns:
            True 表示功能已启用。
        """
        return await FeatureFlagService.is_enabled(self.db, tenant_id, feature_name)

    async def enforce_feature(self, tenant_id: str, feature_name: str) -> None:
        """强制检查功能开关，未启用时抛出 403。

        Args:
            tenant_id: 租户 ID。
            feature_name: 功能开关名称。

        Raises:
            HTTPException: 403，功能未启用。
        """
        enabled = await self.check_feature(tenant_id, feature_name)
        if not enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"当前订阅计划不支持此功能: {feature_name}",
                headers={"X-Error-Code": ErrorCode.PERMISSION_DENIED},
            )

    # ------------------------------------------------------------------
    # Page quota checks
    # ------------------------------------------------------------------

    async def check_page_limit(
        self, tenant_id: str
    ) -> Tuple[bool, int, int]:
        """检查页面数量是否在配额内。

        从 TenantFeatures 的 ``lowcode_max_pages`` 字段读取上限值，
        再与租户实际页面数量比较。

        Returns:
            (allowed, current_count, max_limit)
            - allowed: 是否允许再创建页面
            - current_count: 当前页面总数
            - max_limit: 最大页面数（0 表示不限制）
        """
        # 读取配额上限
        features = await FeatureFlagService.get_tenant_features(self.db, tenant_id)
        max_pages: int = features.get("lowcode_max_pages", 5)

        # 统计当前页面数
        current_count = await self.db.scalar(
            select(func.count(LowCodePage.id)).where(
                LowCodePage.tenant_id == tenant_id
            )
        ) or 0

        # max_pages == 0 表示不限制
        if max_pages <= 0:
            return True, current_count, 0

        return current_count < max_pages, current_count, max_pages

    async def enforce_page_limit(self, tenant_id: str) -> None:
        """强制检查页面配额，超限时抛出 403。

        Raises:
            HTTPException: 403，页面数已达上限。
        """
        allowed, current, max_limit = await self.check_page_limit(tenant_id)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"低代码页面数量已达上限 ({current}/{max_limit})",
                headers={"X-Error-Code": ErrorCode.QUOTA_EXCEEDED},
            )
