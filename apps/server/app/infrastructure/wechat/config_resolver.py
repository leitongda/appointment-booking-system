"""微信小程序配置兼容解析器。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.secret_refs import resolve_secret_ref
from app.models.miniapp_platform import MiniappInstance
from app.models.store import Store


@dataclass
class MiniappWechatConfig:
    app_id: str
    app_secret: str
    source: str
    miniapp_instance_id: Optional[str] = None
    store_id: Optional[str] = None


class WechatConfigResolver:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve(
        self,
        store_id: Optional[str] = None,
        miniapp_instance_id: Optional[str] = None,
    ) -> Optional[MiniappWechatConfig]:
        fallback_store_id = store_id

        if miniapp_instance_id:
            result = await self.db.execute(
                select(MiniappInstance).where(MiniappInstance.id == miniapp_instance_id)
            )
            instance = result.scalar_one_or_none()
            if instance:
                fallback_store_id = fallback_store_id or instance.default_store_id
                instance_secret = resolve_secret_ref(instance.app_secret_ref)
                if instance.status == 1 and instance.app_id and instance_secret:
                    return MiniappWechatConfig(
                        app_id=instance.app_id,
                        app_secret=instance_secret,
                        source="miniapp_instance",
                        miniapp_instance_id=instance.id,
                        store_id=fallback_store_id,
                    )

        if fallback_store_id:
            result = await self.db.execute(
                select(Store).where(Store.id == fallback_store_id)
            )
            store = result.scalar_one_or_none()
            if store and store.wechat_app_id and store.wechat_app_secret:
                return MiniappWechatConfig(
                    app_id=store.wechat_app_id,
                    app_secret=store.wechat_app_secret,
                    source="store",
                    miniapp_instance_id=miniapp_instance_id,
                    store_id=store.id,
                )

        return None
