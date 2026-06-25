
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.notification import CHANNEL_FIELD_MAP as _CHANNEL_FIELD_MAP
from app.constants.notification import TYPE_FIELD_MAP as _TYPE_FIELD_MAP_SHARED
from app.models.notification_preference import NotificationPreference
from app.schemas.notification_preference import NotificationPreferenceUpdate

# 本模块的类型映射：与共享常量大部分一致，但保留差异键以维持现有行为
_TYPE_FIELD_MAP = {
    **_TYPE_FIELD_MAP_SHARED,
    # 以下键覆盖或补充共享映射
    "reminder": "reminder_enabled",        # 本模块特有别名
    "queue_call": "queue_call_enabled",    # 共享映射为 appointment_enabled，本模块使用 queue_call_enabled
}


class NotificationPreferenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(
        self,
        user_id: str,
        user_type: str,
        tenant_id: str | None = None,
    ) -> NotificationPreference:
        stmt = select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.user_type == user_type,
        )
        result = await self.db.execute(stmt)
        pref = result.scalar_one_or_none()

        if pref:
            return pref

        pref = NotificationPreference(
            user_id=user_id,
            user_type=user_type,
            tenant_id=tenant_id,
        )
        self.db.add(pref)
        await self.db.commit()
        await self.db.refresh(pref)
        return pref

    async def update(
        self,
        user_id: str,
        user_type: str,
        data: NotificationPreferenceUpdate,
        tenant_id: str | None = None,
    ) -> NotificationPreference:
        pref = await self.get_or_create(user_id, user_type, tenant_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(pref, field, value)

        await self.db.commit()
        await self.db.refresh(pref)
        return pref

    async def is_channel_enabled(
        self,
        user_id: str,
        user_type: str,
        channel: str,
        tenant_id: str | None = None,
    ) -> bool:
        field = _CHANNEL_FIELD_MAP.get(channel)
        if not field:
            return True
        pref = await self.get_or_create(user_id, user_type, tenant_id)
        return getattr(pref, field, True)

    async def is_type_enabled(
        self,
        user_id: str,
        user_type: str,
        message_type: str,
        tenant_id: str | None = None,
    ) -> bool:
        field = _TYPE_FIELD_MAP.get(message_type)
        if not field:
            return True
        pref = await self.get_or_create(user_id, user_type, tenant_id)
        return getattr(pref, field, True)
