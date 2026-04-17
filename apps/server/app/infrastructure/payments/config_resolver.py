"""支付配置兼容解析器。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id
from app.models.miniapp_platform import MiniappInstance, PaymentProfile, PaymentRoute


@dataclass
class PaymentRoutingConfig:
    payment_profile_id: str
    mode: str
    app_id: Optional[str]
    mch_id: Optional[str]
    sub_mchid: Optional[str]
    notify_url: Optional[str]
    source: str


class PaymentConfigResolver:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve(
        self,
        *,
        store_id: Optional[str] = None,
        miniapp_instance_id: Optional[str] = None,
        payment_profile_id: Optional[str] = None,
    ) -> Optional[PaymentRoutingConfig]:
        tenant_id = get_current_tenant_id()

        if payment_profile_id:
            stmt = select(PaymentProfile).where(
                PaymentProfile.id == payment_profile_id,
                PaymentProfile.status == 1,
            )
            if tenant_id:
                stmt = stmt.where(PaymentProfile.tenant_id == tenant_id)
            result = await self.db.execute(stmt)
            profile = result.scalar_one_or_none()
            if profile:
                return self._serialize(profile, source="payment_profile")

        if store_id:
            route_stmt = (
                select(PaymentRoute, PaymentProfile)
                .join(PaymentProfile, PaymentProfile.id == PaymentRoute.payment_profile_id)
                .where(
                    PaymentRoute.store_id == store_id,
                    PaymentRoute.status == 1,
                    PaymentProfile.status == 1,
                )
            )
            if tenant_id:
                route_stmt = route_stmt.where(PaymentRoute.tenant_id == tenant_id)
            route_stmt = route_stmt.order_by(
                PaymentRoute.priority.desc(), PaymentRoute.created_at.desc()
            )
            result = await self.db.execute(route_stmt)
            matched = result.first()
            if matched:
                _, profile = matched
                return self._serialize(profile, source="store_route")

        if miniapp_instance_id:
            inst_stmt = select(MiniappInstance).where(
                MiniappInstance.id == miniapp_instance_id,
                MiniappInstance.status == 1,
            )
            if tenant_id:
                inst_stmt = inst_stmt.where(MiniappInstance.tenant_id == tenant_id)
            result = await self.db.execute(inst_stmt)
            instance = result.scalar_one_or_none()
            if instance and instance.default_payment_profile_id:
                profile_stmt = select(PaymentProfile).where(
                    PaymentProfile.id == instance.default_payment_profile_id,
                    PaymentProfile.status == 1,
                )
                if tenant_id:
                    profile_stmt = profile_stmt.where(PaymentProfile.tenant_id == tenant_id)
                result = await self.db.execute(profile_stmt)
                profile = result.scalar_one_or_none()
                if profile:
                    return self._serialize(profile, source="miniapp_instance_default")

        default_stmt = select(PaymentProfile).where(
            PaymentProfile.is_default.is_(True),
            PaymentProfile.status == 1,
        )
        if tenant_id:
            default_stmt = default_stmt.where(PaymentProfile.tenant_id == tenant_id)
        default_stmt = default_stmt.order_by(PaymentProfile.created_at.desc())
        result = await self.db.execute(default_stmt)
        profile = result.scalar_one_or_none()
        if profile:
            return self._serialize(profile, source="tenant_default")

        return None

    @staticmethod
    def _serialize(profile: PaymentProfile, source: str) -> PaymentRoutingConfig:
        return PaymentRoutingConfig(
            payment_profile_id=profile.id,
            mode=profile.mode,
            app_id=profile.app_id,
            mch_id=profile.mch_id,
            sub_mchid=profile.sub_mchid,
            notify_url=profile.notify_url,
            source=source,
        )
