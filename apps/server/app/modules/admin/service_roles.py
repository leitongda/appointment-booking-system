"""Role service for admin domain."""

import json
import uuid

from sqlalchemy import and_, func, select

from app.models.admin import Admin, Role
from app.utils.audit import set_create_audit, set_update_audit

# 系统保留角色编码：租户侧不得创建/改名占用，避免与平台特权判定冲突
RESERVED_ROLE_CODES = {
    "SUPER_ADMIN",
    "PLATFORM_ADMIN",
    "TENANT_ADMIN",
    "STORE_ADMIN",
    "STORE_USER",
    "OPERATOR",
    "ADMIN",
}


def _assert_code_not_reserved(code: str | None) -> None:
    if code and code.strip().upper() in RESERVED_ROLE_CODES:
        raise ValueError("该角色编码为系统保留，禁止使用")


def _assert_permissions_scoped(permissions: list[str] | None, tenant_id: str | None) -> None:
    """租户角色不得使用通配权限（平台权限只属于平台角色）"""
    if tenant_id and permissions and "*" in permissions:
        raise ValueError("租户角色不允许使用通配权限（*）")


class RoleService:
    def __init__(self, db):
        self.db = db

    async def get_list(
        self,
        status: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 10,
        tenant_id: str | None = None,
    ) -> tuple[list[Role], int]:
        # 租户隔离：只查询当前租户的角色
        query = select(Role)
        conditions = []
        if tenant_id:
            conditions.append(Role.tenant_id == tenant_id)
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

    async def get_all(self, tenant_id: str | None = None) -> list[Role]:
        # 租户隔离：只查询当前租户的角色
        conditions = []
        if tenant_id:
            conditions.append(Role.tenant_id == tenant_id)
        conditions.append(Role.status == 1)
        query = select(Role).where(and_(*conditions)).order_by(Role.created_at.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, role_id: str, tenant_id: str | None = None) -> Role | None:
        # 租户隔离：查询时附加租户过滤
        if tenant_id:
            result = await self.db.execute(
                select(Role).where(Role.id == role_id, Role.tenant_id == tenant_id)
            )
            return result.scalar_one_or_none()
        return await self.db.get(Role, role_id)

    async def get_by_code(self, code: str, tenant_id: str | None = None) -> Role | None:
        # 租户隔离：编码唯一性检查需限定在租户范围内
        conditions = [Role.code == code]
        if tenant_id:
            conditions.append(Role.tenant_id == tenant_id)
        result = await self.db.execute(select(Role).where(and_(*conditions)))
        return result.scalar_one_or_none()

    async def create(self, data: dict, operator_id: str | None = None, tenant_id: str | None = None) -> Role:
        # 租户隔离：编码唯一性检查需限定在租户范围内
        existing = await self.get_by_code(data["code"], tenant_id=tenant_id)
        if existing:
            raise ValueError("角色编码已存在")
        _assert_code_not_reserved(data["code"])

        permissions = data.get("permissions", [])
        _assert_permissions_scoped(permissions, tenant_id)
        role = Role(
            id=str(uuid.uuid4()),
            name=data["name"],
            code=data["code"],
            description=data.get("description"),
            permissions=json.dumps(permissions) if permissions else None,
            status=data.get("status", 1),
            tenant_id=tenant_id,
        )
        set_create_audit(role, operator_id)
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def update(self, role_id: str, data: dict, operator_id: str | None = None, tenant_id: str | None = None) -> Role | None:
        # 租户隔离：查询时附加租户过滤
        role = await self.get_by_id(role_id, tenant_id=tenant_id)
        if not role:
            return None

        if role.code == "SUPER_ADMIN":
            if data.get("code") and data["code"] != "SUPER_ADMIN":
                raise ValueError("超级管理员编码不可修改")
            if data.get("status") == 0:
                raise ValueError("超级管理员角色不可禁用")
            if "permissions" in data:
                raise ValueError("超级管理员权限不可修改，始终拥有所有权限")

        # 禁止把租户自建角色改名为系统保留编码
        _assert_code_not_reserved(data.get("code"))
        if "permissions" in data:
            _assert_permissions_scoped(data.get("permissions"), role.tenant_id)

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
        self, role_id: str, permissions: list[str], operator_id: str | None = None, tenant_id: str | None = None
    ) -> Role | None:
        # 租户隔离：查询时附加租户过滤
        role = await self.get_by_id(role_id, tenant_id=tenant_id)
        if not role:
            return None

        if role.code == "SUPER_ADMIN":
            raise ValueError("超级管理员权限不可修改，始终拥有所有权限")

        _assert_permissions_scoped(permissions, role.tenant_id)
        role.permissions = json.dumps(permissions)
        set_update_audit(role, operator_id)
        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def delete(self, role_id: str, tenant_id: str | None = None) -> bool:
        # 租户隔离：查询时附加租户过滤
        role = await self.get_by_id(role_id, tenant_id=tenant_id)
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
