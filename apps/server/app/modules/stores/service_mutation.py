"""Mutation helpers for stores."""

import uuid
from typing import List, Optional

from sqlalchemy import and_, delete, func, select

from app.models.admin import Admin, admin_stores
from app.models.department import Department
from app.models.store import Store
from app.schemas.store import StoreCreate, StoreUpdate
from app.utils.audit import set_create_audit, set_update_audit


class StoreMutationMixin:
    async def create(self, data: StoreCreate, operator_id: Optional[str] = None) -> Store:
        if data.code:
            existing = await self.get_by_code(data.code)
            if existing:
                raise ValueError(f"门店编码 {data.code} 已存在")

        # 配额检查（获取当前租户ID）
        from app.common.quota import check_quota
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()
        await check_quota(tenant_id, "stores", self.db)

        store_data = data.model_dump()
        if not store_data.get("password"):
            store_data["password"] = "123456"

        # 设置租户ID
        store_data["tenant_id"] = tenant_id

        store = Store(id=str(uuid.uuid4()), **store_data)
        set_create_audit(store, operator_id)
        self.db.add(store)
        await self.db.commit()
        await self.db.refresh(store)
        return store

    async def update(
        self, store_id: str, data: StoreUpdate, operator_id: Optional[str] = None
    ) -> Optional[Store]:
        store = await self.get_by_id(store_id)
        if not store:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "code" in update_data and update_data["code"]:
            existing = await self.get_by_code(update_data["code"])
            if existing and existing.id != store_id:
                raise ValueError(f"门店编码 {update_data['code']} 已存在")

        for field, value in update_data.items():
            setattr(store, field, value)

        set_update_audit(store, operator_id)
        await self.db.commit()
        await self.db.refresh(store)
        return store

    async def delete(self, store_id: str) -> bool:
        store = await self.get_by_id(store_id)
        if not store:
            return False

        result = await self.db.execute(
            select(func.count(Department.id)).where(Department.store_id == store_id)
        )
        if result.scalar() > 0:
            raise ValueError("该门店下有关联科室，请先删除或转移科室")

        await self.db.delete(store)
        await self.db.commit()
        return True

    async def update_status(self, store_id: str, status: int) -> Optional[Store]:
        store = await self.get_by_id(store_id)
        if not store:
            return None
        store.status = status
        await self.db.commit()
        await self.db.refresh(store)
        return store

    async def batch_bind_departments(self, store_id: str, department_ids: List[str]) -> int:
        from app.middleware.tenant_context import get_current_tenant_id
        store = await self.get_by_id(store_id)
        if not store:
            raise ValueError("门店不存在")

        # 租户隔离校验
        tenant_id = get_current_tenant_id()
        if tenant_id and store.tenant_id and store.tenant_id != tenant_id:
            raise ValueError("无权操作此门店")

        current_departments = await self.get_departments(store_id)
        current_ids = {d.id for d in current_departments}
        new_ids = set(department_ids)

        to_unbind = current_ids - new_ids
        if to_unbind:
            result = await self.db.execute(select(Department).where(Department.id.in_(to_unbind)))
            for dept in result.scalars().all():
                dept.store_id = None

        to_bind = new_ids - current_ids
        if to_bind:
            result = await self.db.execute(select(Department).where(Department.id.in_(to_bind)))
            for dept in result.scalars().all():
                if dept.store_id is None:
                    dept.store_id = store_id

        await self.db.commit()
        return len(department_ids)

    async def batch_bind_admins(self, store_id: str, admin_ids: List[str]) -> int:
        from app.middleware.tenant_context import get_current_tenant_id
        store = await self.get_by_id(store_id)
        if not store:
            raise ValueError("门店不存在")

        # 租户隔离校验
        tenant_id = get_current_tenant_id()
        if tenant_id and store.tenant_id and store.tenant_id != tenant_id:
            raise ValueError("无权操作此门店")

        current_admins = await self.get_admins(store_id)
        current_ids = {a.id for a in current_admins}
        new_ids = set(admin_ids)

        to_unbind = current_ids - new_ids
        if to_unbind:
            await self.db.execute(
                delete(admin_stores).where(
                    and_(admin_stores.c.store_id == store_id, admin_stores.c.admin_id.in_(to_unbind))
                )
            )

        to_bind = new_ids - current_ids
        if to_bind:
            for admin_id in to_bind:
                result = await self.db.execute(select(Admin).where(Admin.id == admin_id))
                admin = result.scalar_one_or_none()
                if admin:
                    await self.db.execute(
                        admin_stores.insert().values(admin_id=admin_id, store_id=store_id)
                    )

        await self.db.commit()
        return len(admin_ids)

    async def update_wechat_config(
        self, store_id: str, config: dict, operator_id: Optional[str] = None
    ) -> Optional[Store]:
        store = await self.get_by_id(store_id)
        if not store:
            return None

        for field, value in config.items():
            if hasattr(store, field):
                setattr(store, field, value)

        set_update_audit(store, operator_id)
        await self.db.commit()
        await self.db.refresh(store)
        return store
