"""Admin response builders and shared helpers."""

import hashlib
import json
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import RedisCache, parse_user_agent
from app.modules.admin.schemas import AdminResponse, RoleResponse, StoreInfo


def parse_permissions(role) -> List[str]:
    if role.permissions:
        try:
            return json.loads(role.permissions)
        except Exception:
            return []
    return []


def build_role_response(role) -> RoleResponse:
    return RoleResponse(
        id=role.id,
        name=role.name,
        code=role.code,
        description=role.description,
        permissions=parse_permissions(role),
        status=role.status,
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


def build_admin_response(admin, permissions: List[str] = None) -> AdminResponse:
    """从 Admin ORM 对象构建 AdminResponse（保留供登录等场景使用）"""
    from app.modules.admin.schemas import TenantStatusInfo

    role_permissions = []
    if permissions is not None:
        role_permissions = permissions
    elif admin.role and admin.role.permissions:
        try:
            role_permissions = json.loads(admin.role.permissions)
        except Exception:
            role_permissions = []

    role_code = admin.role.code if admin.role else None
    is_super_admin = role_code == "SUPER_ADMIN"
    is_store_admin = role_code == "STORE_ADMIN"

    store_ids = []
    stores = []
    if hasattr(admin, "stores") and admin.stores:
        store_ids = [s.id for s in admin.stores]
        stores = [StoreInfo(id=s.id, name=s.name, logo=s.logo, theme_style=s.theme_style) for s in admin.stores]

    can_switch_stores = is_super_admin or (is_store_admin and len(store_ids) > 1)
    current_store = getattr(admin, "current_store", None) or getattr(admin, "store", None)
    current_store_id = getattr(admin, "current_store_id", None) or getattr(admin, "store_id", None)

    # 构建租户状态信息
    tenant_status = None
    tenant = getattr(admin, "tenant", None)
    if tenant:
        days_until_expiry = None
        if tenant.subscription_end_at:
            delta = tenant.subscription_end_at - datetime.utcnow()
            days_until_expiry = max(0, delta.days)
        tenant_status = TenantStatusInfo(
            status=tenant.status,
            subscription_plan_name=tenant.subscription_plan.name if tenant.subscription_plan else None,
            subscription_end_at=tenant.subscription_end_at,
            is_subscription_active=tenant.is_subscription_active,
            days_until_expiry=days_until_expiry,
            contact_phone=tenant.contact_phone,
        )

    return AdminResponse(
        id=admin.id,
        username=admin.username,
        name=admin.name,
        phone=admin.phone,
        email=admin.email,
        avatar=admin.avatar,
        role_id=admin.role_id,
        role_name=admin.role.name if admin.role else None,
        role_code=role_code,
        current_store_id=current_store_id,
        current_store_name=current_store.name if current_store else None,
        store_id=current_store_id,
        store_name=current_store.name if current_store else None,
        store_ids=store_ids,
        stores=stores,
        permissions=role_permissions,
        is_super_admin=is_super_admin,
        is_store_admin=is_store_admin,
        can_view_all_stores=can_switch_stores,
        status=admin.status,
        last_login_at=admin.last_login_at,
        last_login_ip=admin.last_login_ip,
        tenant_id=admin.tenant_id,
        tenant=tenant_status,
        created_at=admin.created_at,
    )


def build_admin_response_from_dict(admin_dict: dict, permissions: List[str] = None) -> AdminResponse:
    """从 get_current_admin 返回的 dict 构建 AdminResponse（避免重复数据库查询）"""
    from app.modules.admin.schemas import TenantStatusInfo

    tenant_data = admin_dict.get("tenant")
    tenant_status = None
    if tenant_data:
        tenant_status = TenantStatusInfo(
            status=tenant_data.get("status", 0),
            subscription_plan_name=tenant_data.get("subscription_plan_name"),
            subscription_end_at=tenant_data.get("subscription_end_at"),
            is_subscription_active=tenant_data.get("is_subscription_active", False),
            days_until_expiry=tenant_data.get("days_until_expiry"),
            contact_phone=tenant_data.get("contact_phone"),
        )

    stores_data = admin_dict.get("stores", [])
    stores = [
        StoreInfo(id=s["id"], name=s["name"], logo=s.get("logo"), theme_style=s.get("theme_style"))
        for s in stores_data
    ]

    return AdminResponse(
        id=admin_dict["id"],
        username=admin_dict.get("username") or "",
        name=admin_dict.get("name"),
        phone=admin_dict.get("phone"),
        email=admin_dict.get("email"),
        avatar=admin_dict.get("avatar"),
        role_id=admin_dict.get("role_id"),
        role_name=admin_dict.get("role_name"),
        role_code=admin_dict.get("role_code"),
        current_store_id=admin_dict.get("current_store_id"),
        current_store_name=admin_dict.get("current_store_name"),
        store_id=admin_dict.get("current_store_id"),
        store_name=admin_dict.get("current_store_name"),
        store_ids=admin_dict.get("store_ids", []),
        stores=stores,
        permissions=permissions or admin_dict.get("permissions", []),
        is_super_admin=admin_dict.get("is_super_admin", False),
        is_store_admin=admin_dict.get("is_store_admin", False),
        can_view_all_stores=admin_dict.get("can_view_all_stores", False),
        status=admin_dict.get("status", 1),
        last_login_at=admin_dict.get("last_login_at"),
        last_login_ip=admin_dict.get("last_login_ip"),
        tenant_id=admin_dict.get("tenant_id"),
        tenant=tenant_status,
        created_at=admin_dict.get("created_at") or datetime.utcnow(),
    )


def build_store_info(store) -> Optional[StoreInfo]:
    if not store:
        return None
    return StoreInfo(
        id=store.id,
        name=store.name,
        logo=store.logo,
        theme_style=store.theme_style,
    )


def build_stores_list(stores) -> Optional[List[StoreInfo]]:
    if not stores:
        return None
    return [build_store_info(s) for s in stores]


async def store_admin_session(
    admin,
    access_token: str,
    client_ip: str,
    user_agent: str,
    db: AsyncSession = None,
) -> None:
    from app.models.admin import AdminLoginHistory
    import uuid

    token_hash = hashlib.sha256(access_token.encode()).hexdigest()[:32]
    device_info = parse_user_agent(user_agent)
    expire_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    expires_at = datetime.utcnow() + timedelta(seconds=expire_seconds)
    login_time = datetime.utcnow()
    login_history_id = str(uuid.uuid4())

    session_data = {
        "admin_id": admin.id,
        "username": admin.username,
        "name": admin.name or admin.username,
        "role_name": admin.role.name if admin.role else None,
        "login_time": login_time.isoformat(),
        "login_ip": client_ip,
        "user_agent": user_agent,
        "token_hash": token_hash,
        "expires_at": expires_at.isoformat(),
        "device_info": device_info,
        "login_history_id": login_history_id,
    }

    # 存储管理员会话，传递 tenant_id 实现多租户隔离
    await RedisCache.set_admin_session(admin.id, session_data, expire_seconds, tenant_id=admin.tenant_id)

    if db:
        login_history = AdminLoginHistory(
            id=login_history_id,
            admin_id=admin.id,
            login_time=login_time,
            login_ip=client_ip,
            user_agent=user_agent,
            browser=device_info.get("browser", "Unknown"),
            os=device_info.get("os", "Unknown"),
            device_type=device_info.get("device_type", "desktop"),
        )
        db.add(login_history)
        await db.commit()
