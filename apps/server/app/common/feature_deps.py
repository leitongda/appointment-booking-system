"""功能开关依赖（P4-8）

提供 `require_feature(name)` 依赖工厂：租户未开通指定功能时返回 403。
受 settings.FEATURE_ENFORCEMENT_ENABLED 灰度控制（默认 False=不拦截），
避免存量租户因默认关闭的开关被误伤。试点接入在线支付。
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth_deps import get_current_user_or_admin
from app.common.feature_flags import FeatureFlagService
from app.core.config import settings
from app.core.error_codes import ErrorCode
from app.db.session import get_db


def require_feature(feature_name: str):
    """功能开关依赖工厂

    用法:
        _: None = Depends(require_feature("online_payment"))
    """

    async def _check_feature(
        current_admin: dict = Depends(get_current_user_or_admin),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        if not settings.FEATURE_ENFORCEMENT_ENABLED:
            return

        tenant_id = current_admin.get("tenant_id")
        if not tenant_id:
            return  # 平台管理员不受租户开关限制

        enabled = await FeatureFlagService.is_enabled(db, tenant_id, feature_name)
        if not enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"当前订阅计划不支持此功能: {feature_name}",
                headers={"X-Error-Code": ErrorCode.PERMISSION_DENIED},
            )

    return _check_feature
