"""Token 和 Session 管理相关端点"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.common.security_settings import get_token_expire_config
from app.core.redis import RedisCache
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.db.session import get_db
from app.models.admin import Admin, Permission
from app.models.tenant import Tenant
from app.modules.admin.helpers import build_admin_response_from_dict
from app.modules.admin.schemas import (
    AdminResponse,
    SwitchStoreRequest,
    SwitchTenantRequest,
)
from app.modules.admin.service_admins import AdminService
from app.schemas.auth import RefreshTokenRequest, TokenResponse

router = APIRouter()
logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


def _build_admin_access_token_payload(admin: Admin) -> dict:
    payload = {"sub": admin.id, "type": "admin"}
    if admin.tenant_id:
        payload["tenant_id"] = admin.tenant_id
    return payload


def _build_admin_refresh_token_payload(admin: Admin) -> dict:
    payload = {"sub": admin.id, "type": "refresh", "role_type": "admin"}
    if admin.tenant_id:
        payload["tenant_id"] = admin.tenant_id
    return payload


@router.post("/refresh", response_model=TokenResponse, summary="刷新管理员Token")
async def refresh_admin_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    payload = decode_token(data.refresh_token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="身份验证失败，请重新登录")

    token_type = payload.get("type")
    role_type = payload.get("role_type")
    is_new_refresh = token_type == "refresh" and role_type == "admin"
    is_legacy_refresh = token_type == "admin"
    if not (is_new_refresh or is_legacy_refresh):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新凭证，请重新登录")

    admin_id = payload.get("sub")
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新凭证，请重新登录")

    service = AdminService(db)
    admin = await service.get_by_id(admin_id)
    if not admin or admin.status != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不存在或已被禁用，请检查后重试")

    token_tenant_id = payload.get("tenant_id")
    if token_tenant_id and token_tenant_id != admin.tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="租户信息不匹配，请重新登录")

    # 轮换 Refresh Token: 将旧 token 加入黑名单
    from datetime import datetime as _dt

    from jose import jwt as _jwt
    try:
        old_claims = _jwt.get_unverified_claims(data.refresh_token)
        exp_ts = old_claims.get("exp", 0)
        remaining_ttl = max(1, int(exp_ts - _dt.utcnow().timestamp()))
    except Exception:
        remaining_ttl = 86400
    await RedisCache.add_refresh_token_to_blacklist(
        data.refresh_token, tenant_id=token_tenant_id, ttl=remaining_ttl
    )

    access_delta, refresh_delta, expires_seconds = await get_token_expire_config(db)
    access_token = create_access_token(data=_build_admin_access_token_payload(admin), expires_delta=access_delta)
    refresh_token = create_refresh_token(data=_build_admin_refresh_token_payload(admin), expires_delta=refresh_delta)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_seconds,
    )


@router.get("/me", response_model=AdminResponse, summary="获取当前管理员信息")
async def get_current_admin_info(
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    # 对超管补充查询权限列表（仅 1 次简单 SELECT，无 selectinload）
    permissions = current_admin.get("permissions", [])
    if current_admin.get("is_super_admin") and permissions == ["*"]:
        perm_result = await db.execute(select(Permission.code).order_by(Permission.sort.asc()))
        permissions = list(perm_result.scalars().all())

    return build_admin_response_from_dict(current_admin, permissions)


@router.post("/logout", summary="退出登录")
async def admin_logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.admin import AdminLoginHistory

    admin_id = current_admin.get("id")
    admin_tenant_id = current_admin.get("tenant_id")
    token = credentials.credentials
    token_hash = __import__("hashlib").sha256(token.encode()).hexdigest()[:32]
    # 传递 tenant_id 实现多租户会话隔离
    session = await RedisCache.get_admin_session(admin_id, tenant_id=admin_tenant_id)
    session_key = RedisCache._build_admin_session_key(admin_id, tenant_id=admin_tenant_id)
    ttl = await RedisCache.ttl(session_key)

    if session:
        login_history_id = session.get("login_history_id")
        login_time_str = session.get("login_time")
        if login_history_id:
            result = await db.execute(select(AdminLoginHistory).where(AdminLoginHistory.id == login_history_id))
            login_history = result.scalar_one_or_none()
            if login_history:
                logout_time = datetime.utcnow()
                login_history.logout_time = logout_time
                login_history.logout_type = "manual"
                if login_time_str:
                    try:
                        login_time = datetime.fromisoformat(login_time_str)
                        login_history.duration = int((logout_time - login_time).total_seconds())
                    except Exception:
                        pass
                await db.commit()

    if ttl > 0:
        # 传递 tenant_id 实现多租户 Token 黑名单隔离
        await RedisCache.add_token_to_blacklist(token_hash, ttl, tenant_id=admin_tenant_id)
    await RedisCache.delete_admin_session(admin_id, tenant_id=admin_tenant_id)
    return {"message": "退出登录成功"}


@router.get("/me/stores", summary="获取绑定门店")
async def get_my_stores(
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    if current_admin.get("is_super_admin"):
        from app.modules.stores.service import StoreService

        store_service = StoreService(db)
        stores, _ = await store_service.get_list(None)
        return {
            "stores": [{"id": s.id, "name": s.name, "logo": s.logo, "themeStyle": s.theme_style} for s in stores],
            "currentStoreId": current_admin.get("current_store_id"),
            "canSwitchStores": True,
        }

    return {
        "stores": current_admin.get("stores", []),
        "currentStoreId": current_admin.get("current_store_id"),
        "canSwitchStores": current_admin.get("can_switch_stores", current_admin.get("can_view_all_stores", False)),
    }


@router.put("/me/current-store", summary="切换当前门店")
async def switch_current_store(
    data: SwitchStoreRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    from app.api.deps import check_store_access
    from app.models.store import Store

    target_store_id = data.store_id
    if not current_admin.get("is_super_admin") and not check_store_access(current_admin, target_store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权访问此门店，请确认您已绑定该门店")

    service = AdminService(db)
    admin = await service.get_by_id(current_admin["id"])
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在，请检查后重试")

    admin.current_store_id = target_store_id
    await db.commit()
    result = await db.execute(select(Store).where(Store.id == target_store_id))
    store = result.scalar_one_or_none()
    return {
        "message": "门店切换成功",
        "currentStore": {"id": store.id, "name": store.name, "logo": store.logo, "themeStyle": store.theme_style} if store else None,
    }


@router.put("/me/current-tenant", summary="切换当前租户")
async def switch_current_tenant(
    data: SwitchTenantRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """切换当前管理员关联的租户（仅平台管理员可用）"""
    # 权限校验：仅平台管理员可切换租户
    if not current_admin.get("is_platform_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="此操作仅限平台管理员")

    target_tenant_id = data.tenant_id

    # 查询目标租户
    result = await db.execute(select(Tenant).where(Tenant.id == target_tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="租户不存在，请检查后重试")

    # 状态校验：只允许切换到正常状态的租户
    if tenant.status != 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="目标租户状态异常，无法切换")

    # 更新管理员的租户关联
    service = AdminService(db)
    admin = await service.get_by_id(current_admin["id"])
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在，请检查后重试")

    admin.tenant_id = target_tenant_id
    await db.commit()

    return {
        "message": "租户切换成功",
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "tenantCode": tenant.tenant_code,
        },
    }
