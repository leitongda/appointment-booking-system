"""Role service for admin domain."""

import json
import uuid
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, select

from app.models.admin import Admin, Role
from app.utils.audit import set_create_audit, set_update_audit


class RoleService:
    def __init__(self, db):
        self.db = db

    async def get_list(
        self,
        status: Optional[int] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Role], int]:
        query = select(Role)
        conditions = []
        if status is not None:
            conditions.append(Role.status == status)
        if keyword:
            conditions.append(Role.name.ilike(f"%{keyword}%"))
        if conditions:
            query = query.where(and_(*conditions))

        count_query = select(func.count(Role.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await self.db.scalar(count_query)

        query = query.order_by(Role.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def get_all(self) -> List[Role]:
        query = select(Role).where(Role.status == 1).order_by(Role.created_at.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, role_id: str) -> Optional[Role]:
        return await self.db.get(Role, role_id)

    async def get_by_code(self, code: str) -> Optional[Role]:
        result = await self.db.execute(select(Role).where(Role.code == code))
        return result.scalar_one_or_none()

    async def create(self, data: dict, operator_id: Optional[str] = None) -> Role:
        existing = await self.get_by_code(data["code"])
        if existing:
            raise ValueError("角色编码已存在")

        permissions = data.get("permissions", [])
        role = Role(
            id=str(uuid.uuid4()),
            name=data["name"],
            code=data["code"],
            description=data.get("description"),
            permissions=json.dumps(permissions) if permissions else None,
            status=data.get("status", 1),
        )
        set_create_audit(role, operator_id)
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def update(self, role_id: str, data: dict, operator_id: Optional[str] = None) -> Optional[Role]:
        role = await self.get_by_id(role_id)
        if not role:
            return None

        if role.code == "SUPER_ADMIN":
            if data.get("code") and data["code"] != "SUPER_ADMIN":
                raise ValueError("超级管理员编码不可修改")
            if data.get("status") == 0:
                raise ValueError("超级管理员角色不可禁用")
            if "permissions" in data:
                raise ValueError("超级管理员权限不可修改，始终拥有所有权限")

        for key, value in data.items():
            if key == "permissions":
                value = json.dumps(value) if value else None
            if hasattr(role, key) and value is not None:
                setattr(role, key, value)

        set_update_audit(role, operator_id)
        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def update_permissions(
        self, role_id: str, permissions: List[str], operator_id: Optional[str] = None
    ) -> Optional[Role]:
        role = await self.get_by_id(role_id)
        if not role:
            return None

        if role.code == "SUPER_ADMIN":
            raise ValueError("超级管理员权限不可修改，始终拥有所有权限")

        role.permissions = json.dumps(permissions)
        set_update_audit(role, operator_id)
        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def delete(self, role_id: str) -> bool:
        role = await self.get_by_id(role_id)
        if not role:
            return False

        if role.code == "SUPER_ADMIN":
            raise ValueError("超级管理员不可删除")

        admin_count = await self.db.scalar(select(func.count(Admin.id)).where(Admin.role_id == role_id))
        if admin_count and admin_count > 0:
            raise ValueError("该角色下有管理员，无法删除")

        await self.db.delete(role)
        await self.db.commit()
        return True
