"""Read helpers for stores."""

from typing import List, Optional

from sqlalchemy import and_, func, select

from app.models.admin import Admin, admin_stores
from app.models.department import Department
from app.models.store import Store
from app.schemas.store import StoreQuery


class StoreQueryMixin:
    async def get_by_id(self, store_id: str) -> Optional[Store]:
        result = await self.db.execute(select(Store).where(Store.id == store_id))
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[Store]:
        result = await self.db.execute(select(Store).where(Store.code == code))
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Store]:
        result = await self.db.execute(select(Store).where(Store.name == name))
        return result.scalar_one_or_none()

    async def check_name_exists(self, name: str, exclude_id: Optional[str] = None) -> bool:
        stmt = select(func.count(Store.id)).where(Store.name == name)
        if exclude_id:
            stmt = stmt.where(Store.id != exclude_id)
        result = await self.db.execute(stmt)
        return (result.scalar() or 0) > 0

    async def check_code_exists(self, code: str, exclude_id: Optional[str] = None) -> bool:
        stmt = select(func.count(Store.id)).where(Store.code == code)
        if exclude_id:
            stmt = stmt.where(Store.id != exclude_id)
        result = await self.db.execute(stmt)
        return (result.scalar() or 0) > 0

    async def get_list(self, query: StoreQuery) -> tuple[List[Store], int]:
        stmt = select(Store)
        count_stmt = select(func.count(Store.id))

        if query.keyword:
            keyword_filter = Store.name.contains(query.keyword) | Store.code.contains(query.keyword)
            stmt = stmt.where(keyword_filter)
            count_stmt = count_stmt.where(keyword_filter)
        if query.status is not None:
            stmt = stmt.where(Store.status == query.status)
            count_stmt = count_stmt.where(Store.status == query.status)
        if query.city:
            stmt = stmt.where(Store.city == query.city)
            count_stmt = count_stmt.where(Store.city == query.city)

        stmt = stmt.order_by(Store.sort_order, Store.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)

        result = await self.db.execute(stmt)
        count_result = await self.db.execute(count_stmt)
        return list(result.scalars().all()), count_result.scalar() or 0

    async def get_all_active(self) -> List[Store]:
        result = await self.db.execute(
            select(Store).where(Store.status == 1).order_by(Store.sort_order)
        )
        return list(result.scalars().all())

    async def get_department_count(self, store_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Department.id)).where(Department.store_id == store_id)
        )
        return result.scalar() or 0

    async def get_departments(self, store_id: str) -> List[Department]:
        result = await self.db.execute(
            select(Department)
            .where(Department.store_id == store_id)
            .order_by(Department.sort_order.desc(), Department.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_admins(self, store_id: str) -> List[Admin]:
        result = await self.db.execute(
            select(Admin)
            .join(admin_stores, Admin.id == admin_stores.c.admin_id)
            .where(admin_stores.c.store_id == store_id)
            .order_by(Admin.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_wechat_config(self, store_id: str) -> Optional[dict]:
        store = await self.get_by_id(store_id)
        if not store:
            return None
        return {
            "app_id": store.wechat_app_id,
            "app_secret": store.wechat_app_secret,
            "mch_id": store.wechat_mch_id,
            "api_key": store.wechat_api_key,
            "notify_url": store.wechat_notify_url,
        }
