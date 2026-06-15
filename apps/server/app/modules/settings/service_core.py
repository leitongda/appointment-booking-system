"""Core key-value accessors for system settings."""

import json
import uuid
from typing import Any

from sqlalchemy import and_, or_, select

from app.models.settings import DEFAULT_SETTINGS, SystemSetting
from app.utils.audit import set_create_audit, set_update_audit


class SettingsCoreMixin:
    async def get_by_category(self, category: str, store_id: str | None = None) -> dict[str, Any]:
        if store_id:
            result = await self.db.execute(
                select(SystemSetting).where(
                    and_(
                        SystemSetting.category == category,
                        or_(SystemSetting.store_id == store_id, SystemSetting.store_id.is_(None)),
                    )
                )
            )
            settings = result.scalars().all()
            data = {}
            global_data = {}
            for setting in settings:
                if setting.store_id == store_id:
                    data[setting.key] = self._parse_value(setting.value)
                else:
                    global_data[setting.key] = self._parse_value(setting.value)
            for key, value in global_data.items():
                if key not in data:
                    data[key] = value
        else:
            result = await self.db.execute(
                select(SystemSetting).where(
                    and_(SystemSetting.category == category, SystemSetting.store_id.is_(None))
                )
            )
            settings = result.scalars().all()
            data = {}
            for setting in settings:
                data[setting.key] = self._parse_value(setting.value)

        defaults = DEFAULT_SETTINGS.get(category, {})
        for key, config in defaults.items():
            if key not in data:
                data[key] = self._parse_value(config["value"])
        return data

    async def get_value(
        self,
        category: str,
        key: str,
        default: Any = None,
        store_id: str | None = None,
    ) -> Any:
        if store_id:
            result = await self.db.execute(
                select(SystemSetting).where(
                    and_(
                        SystemSetting.category == category,
                        SystemSetting.key == key,
                        SystemSetting.store_id == store_id,
                    )
                )
            )
            setting = result.scalar_one_or_none()
            if setting:
                return self._parse_value(setting.value)

        result = await self.db.execute(
            select(SystemSetting).where(
                and_(
                    SystemSetting.category == category,
                    SystemSetting.key == key,
                    SystemSetting.store_id.is_(None),
                )
            )
        )
        setting = result.scalar_one_or_none()
        if setting:
            return self._parse_value(setting.value)

        defaults = DEFAULT_SETTINGS.get(category, {})
        if key in defaults:
            return self._parse_value(defaults[key]["value"])
        return default

    async def set_value(
        self,
        category: str,
        key: str,
        value: Any,
        description: str = None,
        operator_id: str | None = None,
        store_id: str | None = None,
    ) -> SystemSetting:
        if store_id:
            query = select(SystemSetting).where(
                and_(
                    SystemSetting.category == category,
                    SystemSetting.key == key,
                    SystemSetting.store_id == store_id,
                )
            )
        else:
            query = select(SystemSetting).where(
                and_(
                    SystemSetting.category == category,
                    SystemSetting.key == key,
                    SystemSetting.store_id.is_(None),
                )
            )

        result = await self.db.execute(query)
        setting = result.scalar_one_or_none()
        str_value = self._stringify_value(value)

        if setting:
            setting.value = str_value
            if description:
                setting.description = description
            set_update_audit(setting, operator_id)
        else:
            setting = SystemSetting(
                id=str(uuid.uuid4()),
                store_id=store_id,
                category=category,
                key=key,
                value=str_value,
                description=description
                or DEFAULT_SETTINGS.get(category, {}).get(key, {}).get("description"),
            )
            set_create_audit(setting, operator_id)
            self.db.add(setting)

        await self.db.commit()
        await self.db.refresh(setting)
        return setting

    async def delete_store_setting(
        self, category: str, key: str, store_id: str, operator_id: str | None = None
    ) -> bool:
        result = await self.db.execute(
            select(SystemSetting).where(
                and_(
                    SystemSetting.category == category,
                    SystemSetting.key == key,
                    SystemSetting.store_id == store_id,
                )
            )
        )
        setting = result.scalar_one_or_none()
        if setting:
            await self.db.delete(setting)
            await self.db.commit()
            return True
        return False

    async def get_time_periods(self, store_id: str | None = None) -> list[dict[str, Any]]:
        periods = await self.get_value("time_periods", "periods", store_id=store_id)
        default_periods = [
            {"key": "morning", "name": "上午", "startTime": "06:00", "endTime": "12:00"},
            {"key": "afternoon", "name": "下午", "startTime": "12:00", "endTime": "18:00"},
        ]

        if periods is None:
            return default_periods

        if isinstance(periods, str):
            try:
                periods = json.loads(periods)
            except json.JSONDecodeError:
                return default_periods

        return periods

    async def set_time_periods(
        self,
        periods: list[dict[str, Any]],
        store_id: str | None = None,
        operator_id: str | None = None,
    ) -> list[dict[str, Any]]:
        await self.set_value(
            category="time_periods",
            key="periods",
            value=periods,
            description="时段划分配置",
            operator_id=operator_id,
            store_id=store_id,
        )
        return await self.get_time_periods(store_id=store_id)

    async def has_store_time_periods(self, store_id: str) -> bool:
        result = await self.db.execute(
            select(SystemSetting).where(
                and_(
                    SystemSetting.category == "time_periods",
                    SystemSetting.key == "periods",
                    SystemSetting.store_id == store_id,
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def update_category(self, category: str, data: dict[str, Any], store_id: str | None = None) -> dict[str, Any]:
        for key, value in data.items():
            await self.set_value(category, key, value, store_id=store_id)
        return await self.get_by_category(category, store_id=store_id)

    def _parse_value(self, value: str) -> Any:
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            if value == "true":
                return True
            if value == "false":
                return False
            if value.isdigit():
                return int(value)
            try:
                return float(value)
            except (ValueError, TypeError):
                return value

    def _stringify_value(self, value: Any) -> str:
        if isinstance(value, (dict, list, bool)):
            return json.dumps(value, ensure_ascii=False)
        if value is None:
            return "null"
        return str(value)
