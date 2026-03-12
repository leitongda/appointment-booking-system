"""Composed store service."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.stores.service_mutation import StoreMutationMixin
from app.modules.stores.service_query import StoreQueryMixin


class StoreService(StoreQueryMixin, StoreMutationMixin):
    def __init__(self, db: AsyncSession):
        self.db = db
