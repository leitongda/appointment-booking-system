"""Admin account service."""

import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import and_, delete, func, select
from sqlalchemy.orm import selectinload

from app.core.security import get_password_hash, verify_password
from app.middleware.tenant_context import get_current_tenant_id
from app.models.admin import Admin, Role, admin_stores
from app.models.tenant import Tenant
from app.utils.audit import set_create_audit, set_update_audit
from app.common.account_sync import AccountSyncService


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
        tenant_id: Optional[str] = None,  # 支持显式传入租户ID
    ) -> Tuple[List[Admin], int]:
        query = select(Admin).options(
            selectinload(Admin.role),
            selectinload(Admin.tenant).selectinload(Tenant.subscription_plan),
            selectinload(Admin.current_store),
            selectinload(Admin.stores),
        )
        conditions = []

        # 租户过滤：非平台管理员只能看到本租户的管理员
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            conditions.append(Admin.tenant_id == effective_tenant_id)

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

    async def get_by_id(self, admin_id: str, tenant_id: Optional[str] = None) -> Optional[Admin]:
        """根据ID查询管理员

        Args:
            admin_id: 管理员ID
            tenant_id: 租户ID（可选，不传则自动获取当前租户上下文）
        """
        query = (
            select(Admin)
            .options(
                selectinload(Admin.role),
                selectinload(Admin.tenant).selectinload(Tenant.subscription_plan),
                selectinload(Admin.current_store),
                selectinload(Admin.stores),
            )
            .where(Admin.id == admin_id)
        )

        # 租户过滤
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            query = query.where(Admin.tenant_id == effective_tenant_id)

        result = await self.db.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_by_username(self, username: str, tenant_id: Optional[str] = None) -> Optional[Admin]:
        """根据用户名查询管理员

        Args:
            username: 用户名
            tenant_id: 租户ID（可选，用于租户内唯一性检查）
        """
        query = (
            select(Admin)
            .options(
                selectinload(Admin.role),
                selectinload(Admin.tenant).selectinload(Tenant.subscription_plan),
                selectinload(Admin.current_store),
                selectinload(Admin.stores),
            )
            .where(Admin.username == username)
        )

        # 租户过滤（用于唯一性检查场景）
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            query = query.where(Admin.tenant_id == effective_tenant_id)

        result = await self.db.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_by_phone(self, phone: str, tenant_id: Optional[str] = None) -> Optional[Admin]:
        """根据手机号查询管理员

        Args:
            phone: 手机号
            tenant_id: 租户ID（可选，用于租户内唯一性检查）
        """
        query = (
            select(Admin)
            .options(
                selectinload(Admin.role),
                selectinload(Admin.tenant).selectinload(Tenant.subscription_plan),
                selectinload(Admin.current_store),
                selectinload(Admin.stores),
            )
            .where(Admin.phone == phone)
        )

        # 租户过滤（用于唯一性检查场景）
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            query = query.where(Admin.tenant_id == effective_tenant_id)

        result = await self.db.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_by_username_global(self, username: str) -> Optional[Admin]:
        """根据用户名查询管理员（全局查询，不限制租户，用于登录认证）"""
        result = await self.db.execute(
            select(Admin)
            .options(
                selectinload(Admin.role),
                selectinload(Admin.tenant).selectinload(Tenant.subscription_plan),
                selectinload(Admin.current_store),
                selectinload(Admin.stores),
            )
            .where(Admin.username == username)
        )
        return result.unique().scalar_one_or_none()

    async def get_by_phone_global(self, phone: str) -> Optional[Admin]:
        """根据手机号查询管理员（全局查询，不限制租户，用于登录认证）"""
        result = await self.db.execute(
            select(Admin)
            .options(
                selectinload(Admin.role),
                selectinload(Admin.tenant).selectinload(Tenant.subscription_plan),
                selectinload(Admin.current_store),
                selectinload(Admin.stores),
            )
            .where(Admin.phone == phone)
        )
        return result.unique().scalar_one_or_none()

    async def authenticate(self, username: str, password: str) -> Optional[Admin]:
        """用户名密码认证（全局查询，用于登录）"""
        admin = await self.get_by_username_global(username)
        if not admin or not verify_password(password, admin.password_hash):
            return None
        return admin

    async def authenticate_by_phone(self, phone: str, password: str) -> Optional[Admin]:
        """手机号密码认证（全局查询，用于登录）"""
        admin = await self.get_by_phone_global(phone)
        if not admin or not admin.password_hash or not verify_password(password, admin.password_hash):
            return None
        return admin

    async def create(self, data: dict, operator_id: Optional[str] = None) -> Admin:
        # 租户内检查用户名唯一性
        existing = await self.get_by_username(data["username"])
        if existing:
            raise ValueError("用户名已存在")

        # 获取租户ID
        tenant_id = data.get("tenant_id") or get_current_tenant_id()

        # 配额检查（使用租户ID）
        from app.common.quota import check_quota
        await check_quota(tenant_id, "admins", self.db)

        password = data.get("password") or "123456"

        # 密码策略校验
        from app.modules.tenants.password_policy import get_tenant_password_policy, PasswordPolicyValidator
        policy = await get_tenant_password_policy(self.db, tenant_id)
        validator = PasswordPolicyValidator(policy)
        is_valid, errors = validator.validate(
            password,
            username=data.get("username"),
            phone=data.get("phone"),
        )
        if not is_valid:
            raise ValueError("; ".join(errors))

        store_ids = data.get("store_ids") or []
        current_store_id = data.get("store_id") or data.get("current_store_id")
        if current_store_id and current_store_id not in store_ids:
            store_ids.append(current_store_id)
        if store_ids and not current_store_id:
            current_store_id = store_ids[0]

        # 获取租户ID
        tenant_id = data.get("tenant_id") or get_current_tenant_id()

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
            tenant_id=tenant_id,
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

        # 双写同步: Admin -> accounts + account_admins
        await AccountSyncService.sync_admin_to_account(
            self.db, admin.id, operator_id=operator_id
        )

        await self.db.commit()
        return await self.get_by_id(admin.id)

    async def update(self, admin_id: str, data: dict, operator_id: Optional[str] = None) -> Optional[Admin]:
        admin = await self.get_by_id(admin_id)
        if not admin:
            return None

        if data.get("username") and data["username"] != admin.username:
            # 租户内检查用户名唯一性
            existing = await self.get_by_username(data["username"])
            if existing:
                raise ValueError("用户名已存在")

        # 密码策略校验
        if data.get("password"):
            from app.modules.tenants.password_policy import get_tenant_password_policy, PasswordPolicyValidator
            policy = await get_tenant_password_policy(self.db, admin.tenant_id)
            validator = PasswordPolicyValidator(policy)
            is_valid, errors = validator.validate(
                data["password"],
                username=admin.username,
                phone=admin.phone,
            )
            if not is_valid:
                raise ValueError("; ".join(errors))

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
        await self.db.flush()

        # 双写同步: Admin -> accounts + account_admins
        await AccountSyncService.sync_admin_to_account(
            self.db, admin_id, operator_id=operator_id
        )

        await self.db.commit()
        return await self.get_by_id(admin_id)

    async def reset_password(self, admin_id: str, new_password: str) -> bool:
        # 租户过滤：通过 get_by_id 查询，确保不能跨租户重置密码
        admin = await self.get_by_id(admin_id)
        if not admin:
            return False

        # 密码策略校验
        from app.modules.tenants.password_policy import get_tenant_password_policy, PasswordPolicyValidator
        policy = await get_tenant_password_policy(self.db, admin.tenant_id)
        validator = PasswordPolicyValidator(policy)
        is_valid, errors = validator.validate(
            new_password,
            username=admin.username,
            phone=admin.phone,
        )
        if not is_valid:
            raise ValueError("; ".join(errors))

        admin.password_hash = get_password_hash(new_password)
        await self.db.flush()

        # 双写同步: 密码变更同步到 accounts
        await AccountSyncService.sync_admin_to_account(
            self.db, admin_id, operator_id=None
        )

        await self.db.commit()
        return True

    async def update_login_info(self, admin_id: str, ip: str) -> None:
        admin = await self.db.get(Admin, admin_id)
        if admin:
            admin.last_login_at = datetime.now()
            admin.last_login_ip = ip
            await self.db.flush()

            # 双写同步: 登录信息同步到 accounts
            await AccountSyncService.update_admin_login_info(
                self.db, admin_id, ip
            )

            await self.db.commit()

    async def delete(self, admin_id: str) -> bool:
        admin = await self.get_by_id(admin_id)
        if not admin:
            return False

        if admin.role and admin.role.code == "SUPER_ADMIN":
            # 租户过滤：只在当前租户范围内统计超级管理员数量
            count_query = select(func.count(Admin.id)).join(Role).where(Role.code == "SUPER_ADMIN")
            effective_tenant_id = get_current_tenant_id()
            if effective_tenant_id:
                count_query = count_query.where(Admin.tenant_id == effective_tenant_id)
            super_admin_count = await self.db.scalar(count_query)
            if super_admin_count and super_admin_count <= 1:
                raise ValueError("不能删除最后一个超级管理员")

        await self.db.delete(admin)
        await self.db.flush()

        # 双写同步: 从 accounts 删除对应记录
        await AccountSyncService.delete_admin_from_account(
            self.db, admin_id
        )

        await self.db.commit()
        return True
