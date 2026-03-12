"""Permission service for admin domain."""

import json
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.admin import Admin, Permission


class PermissionService:
    def __init__(self, db):
        self.db = db

    async def get_all(self) -> List[Permission]:
        query = select(Permission).order_by(Permission.sort.asc(), Permission.created_at.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_tree(self) -> List[Dict[str, Any]]:
        permissions = await self.get_all()
        perm_dict = {
            p.code: {
                "id": p.id,
                "code": p.code,
                "name": p.name,
                "type": p.type,
                "parentCode": p.parent_code,
                "icon": p.icon,
                "sort": p.sort,
                "children": [],
            }
            for p in permissions
        }

        tree = []
        for p in permissions:
            node = perm_dict[p.code]
            if p.parent_code and p.parent_code in perm_dict:
                perm_dict[p.parent_code]["children"].append(node)
            else:
                tree.append(node)
        return tree

    async def get_by_code(self, code: str) -> Optional[Permission]:
        result = await self.db.execute(select(Permission).where(Permission.code == code))
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Permission:
        existing = await self.get_by_code(data["code"])
        if existing:
            raise ValueError("权限码已存在")

        permission = Permission(
            id=str(uuid.uuid4()),
            code=data["code"],
            name=data["name"],
            type=data["type"],
            parent_code=data.get("parent_code"),
            icon=data.get("icon"),
            sort=data.get("sort", 0),
        )
        self.db.add(permission)
        await self.db.commit()
        await self.db.refresh(permission)
        return permission

    async def batch_create(self, permissions_data: List[dict]) -> List[Permission]:
        created = []
        for data in permissions_data:
            existing = await self.get_by_code(data["code"])
            if not existing:
                permission = Permission(
                    id=str(uuid.uuid4()),
                    code=data["code"],
                    name=data["name"],
                    type=data["type"],
                    parent_code=data.get("parent_code"),
                    icon=data.get("icon"),
                    sort=data.get("sort", 0),
                )
                self.db.add(permission)
                created.append(permission)

        if created:
            await self.db.commit()
        return created

    async def delete(self, code: str) -> bool:
        permission = await self.get_by_code(code)
        if not permission:
            return False

        await self.db.delete(permission)
        await self.db.commit()
        return True

    async def get_admin_permissions(self, admin_id: str) -> List[str]:
        result = await self.db.execute(
            select(Admin).options(selectinload(Admin.role)).where(Admin.id == admin_id)
        )
        admin = result.unique().scalar_one_or_none()
        if not admin or not admin.role:
            return []

        if admin.role.code == "SUPER_ADMIN":
            all_perms = await self.get_all()
            return [p.code for p in all_perms]

        if admin.role.permissions:
            try:
                return json.loads(admin.role.permissions)
            except Exception:
                return []
        return []
