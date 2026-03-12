"""Admin account service."""

import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import and_, delete, func, select
from sqlalchemy.orm import selectinload

from app.core.security import get_password_hash, verify_password
from app.models.admin import Admin, Role, admin_stores
from app.utils.audit import set_create_audit, set_update_audit


class AdminService:
    def __init__(self, db):
        self.db = db

    async def get_list(
        self,
        role_id: Optional[str] = None,
        status: Optional[int] = None,
        keyword: Optional[str] = None,
        store_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Admin], int]:
        query = select(Admin).options(
            selectinload(Admin.role),
            selectinload(Admin.current_store),
            selectinload(Admin.stores),
        )
        conditions = []
        if role_id:
            conditions.append(Admin.role_id == role_id)
        if status is not None:
            conditions.append(Admin.status == status)
        if keyword:
            conditions.append(
                Admin.username.ilike(f"%{keyword}%")
                | Admin.name.ilike(f"%{keyword}%")
                | Admin.phone.ilike(f"%{keyword}%")
            )
        if store_id is not None:
            query = query.join(admin_stores, Admin.id == admin_stores.c.admin_id)
            conditions.append(admin_stores.c.store_id == store_id)
        if conditions:
            query = query.where(and_(*conditions))

        count_query = select(func.count(Admin.id))
        if store_id is not None:
            count_query = count_query.join(admin_stores, Admin.id == admin_stores.c.admin_id)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await self.db.scalar(count_query)

        query = query.order_by(Admin.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.unique().scalars().all()
        return list(items), total or 0

    async def get_by_id(self, admin_id: str) -> Optional[Admin]:
        result = await self.db.execute(
            select(Admin)
            .options(
                selectinload(Admin.role),
                selectinload(Admin.current_store),
                selectinload(Admin.stores),
            )
            .where(Admin.id == admin_id)
        )
        return result.unique().scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[Admin]:
        result = await self.db.execute(
            select(Admin)
            .options(
                selectinload(Admin.role),
                selectinload(Admin.current_store),
                selectinload(Admin.stores),
            )
            .where(Admin.username == username)
        )
        return result.unique().scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> Optional[Admin]:
        result = await self.db.execute(
            select(Admin)
            .options(
                selectinload(Admin.role),
                selectinload(Admin.current_store),
                selectinload(Admin.stores),
            )
            .where(Admin.phone == phone)
        )
        return result.unique().scalar_one_or_none()

    async def authenticate(self, username: str, password: str) -> Optional[Admin]:
        admin = await self.get_by_username(username)
        if not admin or not verify_password(password, admin.password_hash):
            return None
        return admin

    async def authenticate_by_phone(self, phone: str, password: str) -> Optional[Admin]:
        admin = await self.get_by_phone(phone)
        if not admin or not admin.password_hash or not verify_password(password, admin.password_hash):
            return None
        return admin

    async def create(self, data: dict, operator_id: Optional[str] = None) -> Admin:
        existing = await self.get_by_username(data["username"])
        if existing:
            raise ValueError("用户名已存在")

        password = data.get("password") or "123456"
        store_ids = data.get("store_ids") or []
        current_store_id = data.get("store_id") or data.get("current_store_id")
        if current_store_id and current_store_id not in store_ids:
            store_ids.append(current_store_id)
        if store_ids and not current_store_id:
            current_store_id = store_ids[0]

        admin = Admin(
            id=str(uuid.uuid4()),
            username=data["username"],
            password_hash=get_password_hash(password),
            name=data.get("name"),
            phone=data.get("phone"),
            email=data.get("email"),
            avatar=data.get("avatar"),
            role_id=data.get("role_id"),
            current_store_id=current_store_id,
            status=data.get("status", 1),
        )
        set_create_audit(admin, operator_id)
        self.db.add(admin)
        await self.db.flush()

        if store_ids:
            for store_id in store_ids:
                await self.db.execute(
                    admin_stores.insert().values(
                        admin_id=admin.id,
                        store_id=store_id,
                        is_manager=1 if data.get("role_id") else 0,
                    )
                )

        await self.db.commit()
        return await self.get_by_id(admin.id)

    async def update(self, admin_id: str, data: dict, operator_id: Optional[str] = None) -> Optional[Admin]:
        admin = await self.get_by_id(admin_id)
        if not admin:
            return None

        if data.get("username") and data["username"] != admin.username:
            existing = await self.get_by_username(data["username"])
            if existing:
                raise ValueError("用户名已存在")

        store_ids = data.pop("store_ids", None)
        if "store_id" in data:
            current_store_id = data.pop("store_id")
            if current_store_id:
                data["current_store_id"] = current_store_id
                if store_ids is None:
                    store_ids = [current_store_id]

        for key, value in data.items():
            if key == "password" and value:
                admin.password_hash = get_password_hash(value)
            elif hasattr(admin, key) and value is not None:
                setattr(admin, key, value)

        if store_ids is not None:
            await self.db.execute(delete(admin_stores).where(admin_stores.c.admin_id == admin_id))
            for store_id in store_ids:
                await self.db.execute(
                    admin_stores.insert().values(admin_id=admin_id, store_id=store_id, is_manager=1)
                )
            if admin.current_store_id and admin.current_store_id not in store_ids:
                admin.current_store_id = store_ids[0] if store_ids else None

        set_update_audit(admin, operator_id)
        await self.db.commit()
        return await self.get_by_id(admin_id)

    async def reset_password(self, admin_id: str, new_password: str) -> bool:
        admin = await self.db.get(Admin, admin_id)
        if not admin:
            return False
        admin.password_hash = get_password_hash(new_password)
        await self.db.commit()
        return True

    async def update_login_info(self, admin_id: str, ip: str) -> None:
        admin = await self.db.get(Admin, admin_id)
        if admin:
            admin.last_login_at = datetime.now()
            admin.last_login_ip = ip
            await self.db.commit()

    async def delete(self, admin_id: str) -> bool:
        admin = await self.get_by_id(admin_id)
        if not admin:
            return False

        if admin.role and admin.role.code == "SUPER_ADMIN":
            super_admin_count = await self.db.scalar(
                select(func.count(Admin.id)).join(Role).where(Role.code == "SUPER_ADMIN")
            )
            if super_admin_count and super_admin_count <= 1:
                raise ValueError("不能删除最后一个超级管理员")

        await self.db.delete(admin)
        await self.db.commit()
        return True
