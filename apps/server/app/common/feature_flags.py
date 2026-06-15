"""功能开关服务

统一管理租户功能开关的读取、校验与灰度控制。
"""
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import SubscriptionPlan, Tenant
from app.modules.tenants.schemas import TenantFeatures


class FeatureFlagService:
    """功能开关服务

    读取优先级（高到低）：
    1. 租户级覆盖（tenant.features）
    2. 订阅计划默认（subscription_plan.features）
    3. 系统默认值（TenantFeatures 字段默认值）
    """

    @staticmethod
    def _parse_features_json(features_json: str | None) -> dict[str, Any]:
        """解析 features JSON 字符串为字典"""
        if not features_json:
            return {}
        try:
            data = json.loads(features_json)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}

    @classmethod
    def get_default_features(cls) -> dict[str, bool]:
        """获取系统默认功能开关"""
        return TenantFeatures().model_dump()

    @classmethod
    async def get_tenant_features(cls, db: AsyncSession, tenant_id: str) -> dict[str, bool]:
        """获取租户有效功能开关（合并订阅计划 + 租户覆盖）"""
        result = await db.execute(
            select(Tenant, SubscriptionPlan.features.label("plan_features"))
            .outerjoin(SubscriptionPlan, Tenant.subscription_plan_id == SubscriptionPlan.id)
            .where(Tenant.id == tenant_id)
        )
        row = result.one_or_none()
        if not row:
            return cls.get_default_features()

        tenant, plan_features_json = row

        # 基础默认值
        features = cls.get_default_features()

        # 订阅计划层覆盖
        plan_features = cls._parse_features_json(plan_features_json)
        features.update({k: bool(v) for k, v in plan_features.items() if k in features})

        # 租户层最终覆盖
        tenant_features = cls._parse_features_json(tenant.features)
        features.update({k: bool(v) for k, v in tenant_features.items() if k in features})

        return features

    @classmethod
    async def is_enabled(cls, db: AsyncSession, tenant_id: str, feature_name: str) -> bool:
        """检查指定功能是否对租户启用"""
        features = await cls.get_tenant_features(db, tenant_id)
        return features.get(feature_name, False)

    @classmethod
    async def check_features(
        cls,
        db: AsyncSession,
        tenant_id: str,
        required_features: list[str],
    ) -> tuple[bool, list[str]]:
        """批量检查功能开关

        Returns:
            (是否全部通过, 未启用的功能列表)
        """
        features = await cls.get_tenant_features(db, tenant_id)
        missing = [f for f in required_features if not features.get(f, False)]
        return len(missing) == 0, missing

    @classmethod
    async def get_beta_features(cls, db: AsyncSession, tenant_id: str) -> dict[str, bool]:
        """获取租户的灰度功能列表（仅返回 beta_ 开头的功能）"""
        features = await cls.get_tenant_features(db, tenant_id)
        return {k: v for k, v in features.items() if k.startswith("beta_")}

    @classmethod
    async def is_beta_enabled(cls, db: AsyncSession, tenant_id: str, feature_name: str) -> bool:
        """检查灰度功能是否启用（需要 beta_features 总开关 + 具体功能开关）"""
        if not feature_name.startswith("beta_"):
            return False
        features = await cls.get_tenant_features(db, tenant_id)
        return features.get("beta_features", False) and features.get(feature_name, False)

    @classmethod
    def validate_feature_name(cls, feature_name: str) -> bool:
        """校验功能名称是否合法（是否在 TenantFeatures 中定义）"""
        default_features = cls.get_default_features()
        return feature_name in default_features

    @classmethod
    def sanitize_features(cls, features: dict[str, Any] | None) -> dict[str, bool]:
        """清洗功能开关数据：仅保留已定义字段，统一为布尔值"""
        default_features = cls.get_default_features()
        if not features or not isinstance(features, dict):
            return dict(default_features)

        result = dict(default_features)
        for key, value in features.items():
            if key in result:
                result[key] = bool(value)
        return result
