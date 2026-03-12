"""Composed settings service."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.settings.service_core import SettingsCoreMixin
from app.modules.settings.service_views import SettingsViewMixin


class SettingsService(SettingsCoreMixin, SettingsViewMixin):
    def __init__(self, db: AsyncSession):
        self.db = db
