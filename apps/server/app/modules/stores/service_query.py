"""Read helpers for stores."""


from sqlalchemy import func, select

from app.middleware.tenant_context import get_current_tenant_id
from app.models.admin import Admin, admin_stores
from app.models.department import Department
from app.models.store import Store
from app.schemas.store import StoreQuery


class StoreQueryMixin:
    def _tenant(self, tenant_id: str | None) -> str | None:
        """显式锚点优先；未传时回退请求上下文（公开端兼容）"""
        return tenant_id if tenant_id is not None else get_current_tenant_id()

    async def get_by_id(self, store_id: str, tenant_id: str | None = None) -> Store | None:
        stmt = select(Store).where(Store.id == store_id)
        tenant_id = self._tenant(tenant_id)
        if tenant_id:
            stmt = stmt.where(Store.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str, tenant_id: str | None = None) -> Store | None:
        stmt = select(Store).where(Store.code == code)
        tenant_id = self._tenant(tenant_id)
        if tenant_id:
            stmt = stmt.where(Store.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str, tenant_id: str | None = None) -> Store | None:
        stmt = select(Store).where(Store.name == name)
        tenant_id = self._tenant(tenant_id)
        if tenant_id:
            stmt = stmt.where(Store.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def check_name_exists(self, name: str, exclude_id: str | None = None, tenant_id: str | None = None) -> bool:
        stmt = select(func.count(Store.id)).where(Store.name == name)
        tenant_id = self._tenant(tenant_id)
        if tenant_id:
            stmt = stmt.where(Store.tenant_id == tenant_id)
        if exclude_id:
            stmt = stmt.where(Store.id != exclude_id)
        result = await self.db.execute(stmt)
        return (result.scalar() or 0) > 0

    async def check_code_exists(self, code: str, exclude_id: str | None = None, tenant_id: str | None = None) -> bool:
        stmt = select(func.count(Store.id)).where(Store.code == code)
        tenant_id = self._tenant(tenant_id)
        if tenant_id:
            stmt = stmt.where(Store.tenant_id == tenant_id)
        if exclude_id:
            stmt = stmt.where(Store.id != exclude_id)
        result = await self.db.execute(stmt)
        return (result.scalar() or 0) > 0

    async def get_list(self, query: StoreQuery | None = None, tenant_id: str | None = None) -> tuple[list[Store], int]:
        if query is None:
            query = StoreQuery()

        tenant_id = self._tenant(tenant_id)
        stmt = select(Store)
        count_stmt = select(func.count(Store.id))
        if tenant_id:
            stmt = stmt.where(Store.tenant_id == tenant_id)
            count_stmt = count_stmt.where(Store.tenant_id == tenant_id)

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

    async def get_all_active(self, tenant_id: str | None = None) -> list[Store]:
        stmt = select(Store).where(Store.status == 1)
        tenant_id = self._tenant(tenant_id)
        if tenant_id:
            stmt = stmt.where(Store.tenant_id == tenant_id)
        result = await self.db.execute(stmt.order_by(Store.sort_order))
        return list(result.scalars().all())

    async def get_department_count(self, store_id: str, tenant_id: str | None = None) -> int:
        stmt = select(func.count(Department.id)).where(Department.store_id == store_id)
        tenant_id = self._tenant(tenant_id)
        if tenant_id:
            stmt = stmt.where(Department.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_department_counts_batch(self, store_ids: list[str], tenant_id: str | None = None) -> dict[str, int]:
        """批量查询多个门店的科室数量，解决 N+1 问题。

        Returns:
            dict: {store_id: count}
        """
        if not store_ids:
            return {}
        tenant_id = self._tenant(tenant_id)
        stmt = (
            select(Department.store_id, func.count(Department.id))
            .where(Department.store_id.in_(store_ids))
            .group_by(Department.store_id)
        )
        if tenant_id:
            stmt = stmt.where(Department.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        counts = {row[0]: row[1] for row in result.all()}
        # 没有科室的门店不会出现在结果中，补充为 0
        return {sid: counts.get(sid, 0) for sid in store_ids}

    async def get_departments(self, store_id: str, tenant_id: str | None = None) -> list[Department]:
        stmt = select(Department).where(Department.store_id == store_id)
        tenant_id = self._tenant(tenant_id)
        if tenant_id:
            stmt = stmt.where(Department.tenant_id == tenant_id)
        result = await self.db.execute(
            stmt.order_by(Department.sort_order.desc(), Department.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_admins(self, store_id: str, tenant_id: str | None = None) -> list[Admin]:
        stmt = (
            select(Admin)
            .join(admin_stores, Admin.id == admin_stores.c.admin_id)
            .where(admin_stores.c.store_id == store_id)
        )
        tenant_id = self._tenant(tenant_id)
        if tenant_id:
            stmt = stmt.where(Admin.tenant_id == tenant_id)
        result = await self.db.execute(stmt.order_by(Admin.created_at.desc()))
        return list(result.scalars().all())

    async def get_wechat_config(self, store_id: str, tenant_id: str | None = None) -> dict | None:
        store = await self.get_by_id(store_id, tenant_id=tenant_id)
        if not store:
            return None
        return {
            "app_id": store.wechat_app_id,
            "app_secret": store.wechat_app_secret,
            "mch_id": store.wechat_mch_id,
            "api_key": store.wechat_api_key,
            "notify_url": store.wechat_notify_url,
        }
